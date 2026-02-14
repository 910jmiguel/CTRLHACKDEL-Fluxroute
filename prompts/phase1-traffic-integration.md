# Phase 1: Real-Time Traffic Congestion Integration

> **Portable prompt** — apply on top of any version of the FluxRoute codebase.
> No hardcoded line numbers. Uses discovery instructions to find insertion points.

---

## 1. Overview & Goals

Add real-time traffic congestion visualization to FluxRoute's driving and hybrid routes:

- **Backend:** Extract per-segment congestion data from Mapbox Directions API and expose it through the existing route response
- **Frontend:** Render multi-colored route segments (green → amber → orange → red) with a dark outline underneath (Google Maps style)
- **Traffic tileset:** Show Mapbox Traffic v1 as a semi-transparent map layer, toggleable from the sidebar
- **Route cards:** Display traffic severity badges on driving/hybrid route cards
- **Decision matrix:** Surface traffic conditions in the Zen column
- **Congestion tooltips:** Hover over congestion-colored segments to see severity labels
- **Map legend:** Floating legend showing congestion color meanings
- **Animated pulse:** Subtle animation on severe congestion segments

### Design Decisions (Pre-Confirmed)

- Multi-colored congestion segments WITH dark outline underneath (Google Maps style)
- Traffic badge uses short labels: "Light" / "Moderate" / "Heavy" / "Severe"
- Mapbox Traffic tileset (mapbox://mapbox.mapbox-traffic-v1) as semi-transparent background
- Fallback: flat blue driving route when no congestion data available (never show green as default)
- Merge adjacent coordinates with same congestion level into single sub-segments (avoid hundreds of tiny map layers)

---

## 2. Adaptation Guide — Discovering Insertion Points

This prompt references functions, models, and components by **name**, not by line number. Before implementing each step, locate the target using these strategies:

| What You Need | How to Find It |
|---|---|
| `RouteSegment` Pydantic model | Search `backend/app/models.py` for `class RouteSegment` |
| `RouteOption` Pydantic model | Search `backend/app/models.py` for `class RouteOption` |
| Mapbox Directions helper | Search `backend/app/route_engine.py` for the function that builds a Mapbox Directions API URL (look for `api.mapbox.com/directions` or a function like `_mapbox_directions`) |
| Driving route builder | Search `route_engine.py` for where `RouteOption` is constructed with `mode="driving"` or `RouteMode.driving` |
| Hybrid route builder | Search `route_engine.py` for where `RouteOption` is constructed with `mode="hybrid"` or `RouteMode.hybrid` |
| Stress score calculation | Search `route_engine.py` for `stress_score` assignment on driving/hybrid routes |
| `RouteSegment` TypeScript interface | Search `frontend/lib/types.ts` for `interface RouteSegment` or `type RouteSegment` |
| `RouteOption` TypeScript interface | Search `frontend/lib/types.ts` for `interface RouteOption` or `type RouteOption` |
| Route mode colors | Search `frontend/lib/constants.ts` for `MODE_COLORS` |
| Route drawing function | Search `frontend/lib/mapUtils.ts` for the function that draws route polylines on the map (e.g. `drawRoute`, `drawMultimodalRoute`, or similar) |
| FluxMap route rendering | Search `frontend/components/FluxMap.tsx` for the `useEffect` that renders routes when the `routes` array changes |
| Route card component | Search `frontend/components/RouteCards.tsx` for where each route option is rendered as a card |
| Decision matrix component | Search `frontend/components/DecisionMatrix.tsx` for the Zen/comfort column rendering |
| Sidebar component | Search `frontend/components/Sidebar.tsx` for the sidebar layout |

**General approach for each step:**
1. Read the target file fully
2. Find the named function/model/component
3. Identify the exact insertion point (after which field, inside which block)
4. Make the change

---

## 3. Backend: Models

**File:** `backend/app/models.py`

### 3a. RouteSegment — Add Congestion Fields

Find the `RouteSegment` model (Pydantic BaseModel). Add these fields after the existing `color` field (or at the end of the model):

```python
congestion_level: Optional[str] = None  # "low", "moderate", "heavy", "severe"
congestion_segments: Optional[list[dict]] = None  # Sub-segments with per-segment congestion
```

### 3b. RouteOption — Add Traffic Summary

Find the `RouteOption` model. Add this field after the `summary` field (or at the end):

```python
traffic_summary: Optional[str] = None  # "Light Traffic", "Moderate Traffic", etc.
```

---

## 4. Backend: Congestion Extraction from Mapbox API

**File:** `backend/app/route_engine.py`

### 4a. Add Congestion Annotations to Mapbox Request

Find the function that calls the Mapbox Directions API (the one that builds a URL like `https://api.mapbox.com/directions/v5/mapbox/{profile}/...`).

- Ensure the `profile` used for driving routes is `"driving-traffic"` (not just `"driving"`)
- Add `annotations=congestion` as a query parameter to the URL
- After parsing the response JSON, extract the congestion array:

```python
congestion = None
try:
    congestion = data["routes"][0]["legs"][0]["annotation"]["congestion"]
except (KeyError, IndexError):
    pass
```

- Return the congestion array as a new key in the function's result dict (e.g. `result["congestion"] = congestion`)

### 4b. Add Three Helper Functions

Add these helper functions to `route_engine.py` (before the main route generation function):

**1. Congestion summary calculator:**

```python
def _compute_congestion_summary(congestion_list: list[str]) -> tuple[str, str]:
    """Returns (dominant_level, traffic_label) from Mapbox congestion array."""
    if not congestion_list:
        return ("unknown", "Unknown Traffic")

    from collections import Counter
    counts = Counter(congestion_list)
    total = len(congestion_list)

    # Threshold: if >30% of segments are at a given severity, use that label
    for level, label in [
        ("severe", "Severe Traffic"),
        ("heavy", "Heavy Traffic"),
        ("moderate", "Moderate Traffic"),
    ]:
        if counts.get(level, 0) / total > 0.3:
            return (level, label)

    return ("low", "Light Traffic")
```

**2. Congestion stress score:**

```python
def _congestion_stress_score(congestion_list: list[str]) -> float:
    """Convert congestion data into a stress score contribution (0.0 to 0.3)."""
    if not congestion_list:
        return 0.0

    weights = {"severe": 0.3, "heavy": 0.2, "moderate": 0.1, "low": 0.0, "unknown": 0.0}
    total = sum(weights.get(c, 0.0) for c in congestion_list)
    return total / len(congestion_list)
```

**3. Geometry splitter:**

```python
def _split_geometry_by_congestion(
    coordinates: list[list[float]], congestion_list: list[str]
) -> list[dict]:
    """Split a LineString into sub-segments grouped by congestion level.

    Mapbox returns one congestion value per coordinate pair (N-1 values for N coords).
    Groups consecutive coordinates with the same level into single sub-segments.
    """
    if not congestion_list or len(coordinates) < 2:
        return []

    segments = []
    current_level = congestion_list[0]
    current_coords = [coordinates[0]]

    for i, level in enumerate(congestion_list):
        current_coords.append(coordinates[i + 1])

        # Check if next segment changes level (or we're at the end)
        next_level = congestion_list[i + 1] if i + 1 < len(congestion_list) else None
        if next_level != current_level:
            segments.append({
                "geometry": {
                    "type": "LineString",
                    "coordinates": current_coords,
                },
                "congestion": current_level,
            })
            if next_level is not None:
                current_level = next_level
                current_coords = [coordinates[i + 1]]  # Overlap for continuity

    return segments
```

### 4c. Wire Congestion into Driving Route

Find where the driving `RouteOption` is constructed. After calling the Mapbox directions function:

1. Extract `congestion_data = mapbox_result.get("congestion")`
2. If congestion data exists:
   - Call `_compute_congestion_summary(congestion_data)` → `(congestion_level, traffic_label)`
   - Call `_split_geometry_by_congestion(coordinates, congestion_data)` → `congestion_segments`
   - Set on the driving `RouteSegment`: `congestion_level=congestion_level`, `congestion_segments=congestion_segments`
   - Compute stress: `stress_score = 0.3 + _congestion_stress_score(congestion_data)`
   - Set on `RouteOption`: `traffic_summary=traffic_label`
3. If no congestion data (fallback):
   - Keep existing rush-hour heuristic stress scoring (base 0.5, +0.2 if 7–9am or 5–7pm)
   - Leave `congestion_level`, `congestion_segments`, and `traffic_summary` as `None`
4. Always: add +0.1 to stress if adverse weather

### 4d. Wire Congestion into Hybrid Route

Find where the hybrid `RouteOption` is constructed. The hybrid route has a driving segment — apply the same congestion extraction to it:

1. Extract congestion from the driving segment's Mapbox response
2. If congestion data exists:
   - Set `congestion_level` and `congestion_segments` on the driving `RouteSegment`
   - Stress: `0.25 + _congestion_stress_score(congestion_data) + delay_prob * 0.2`
   - Set `traffic_summary` on the hybrid `RouteOption`
3. If no congestion data (fallback):
   - Stress: `0.35 + delay_prob * 0.2`

---

## 5. Frontend: Types & Constants

### 5a. TypeScript Types

**File:** `frontend/lib/types.ts`

Find the `RouteSegment` interface. Add:

```typescript
congestion_level?: "low" | "moderate" | "heavy" | "severe";
congestion_segments?: Array<{
  geometry: GeoJSON.LineString;
  congestion: string;
}>;
```

Find the `RouteOption` interface. Add:

```typescript
traffic_summary?: string;
```

### 5b. Congestion Color Constants

**File:** `frontend/lib/constants.ts`

Add after the existing `MODE_COLORS` constant:

```typescript
export const CONGESTION_COLORS: Record<string, string> = {
  low: "#10B981",      // Green
  moderate: "#F59E0B", // Amber
  heavy: "#F97316",    // Orange
  severe: "#EF4444",   // Red
  unknown: "#3B82F6",  // Blue (fallback)
};
```

---

## 6. Map Rendering: Congestion-Colored Routes

**File:** `frontend/lib/mapUtils.ts`

Find the function that draws route polylines on the map (e.g. `drawMultimodalRoute` or `drawRoute`). Import `CONGESTION_COLORS` from constants.

Modify the segment rendering logic:

**When a segment has `congestion_segments` data:**
1. Draw a dark outline first using the full segment geometry:
   - Color: `#1a1a2e`
   - Width: `isSelected ? 8 : 5`
   - This goes underneath the colored segments
2. Draw each congestion sub-segment on top:
   - Color: `CONGESTION_COLORS[sub.congestion]` (fall back to `CONGESTION_COLORS.unknown`)
   - Width: `isSelected ? 5 : 3`
   - Each sub-segment gets a unique layer ID (e.g. `route-{id}-seg-{segIdx}-cong-{subIdx}`)

**When a segment has NO `congestion_segments`:**
- Keep the existing single-color rendering unchanged (use `segment.color` or mode color)

---

## 7. Traffic Tileset + Toggle

### 7a. Traffic Tileset Layer

**File:** `frontend/components/FluxMap.tsx`

In the `useEffect` that handles route rendering (triggered when the `routes` array changes):

When `routes.length > 0`, add the Mapbox Traffic tileset as a background layer:

```typescript
// Add traffic source
if (!map.getSource("mapbox-traffic")) {
  map.addSource("mapbox-traffic", {
    type: "vector",
    url: "mapbox://mapbox.mapbox-traffic-v1",
  });
}

// Add traffic layer BEFORE route layers (so routes render on top)
if (!map.getLayer("traffic-flow-layer")) {
  map.addLayer({
    id: "traffic-flow-layer",
    type: "line",
    source: "mapbox-traffic",
    "source-layer": "traffic",
    paint: {
      "line-color": [
        "match", ["get", "congestion"],
        "low", CONGESTION_COLORS.low,
        "moderate", CONGESTION_COLORS.moderate,
        "heavy", CONGESTION_COLORS.heavy,
        "severe", CONGESTION_COLORS.severe,
        CONGESTION_COLORS.unknown,
      ],
      "line-width": 1.5,
      "line-opacity": 0.4,
    },
  });
}
```

When routes are cleared, remove the traffic layer and source.

### 7b. Traffic Toggle Button (NEW)

**File:** `frontend/components/Sidebar.tsx` (or a new `TrafficToggle` component)

Add a toggle button in the sidebar that shows/hides the traffic tileset independently of route searches:

- **Label:** "Traffic" with a car/road icon
- **Behavior:** Toggles `traffic-flow-layer` visibility via `map.setLayoutProperty("traffic-flow-layer", "visibility", "visible" | "none")`
- **State:** Use a `showTraffic` boolean state, default `true` when routes are displayed
- **Position:** Below the route search input, above the route cards
- **Style:** Glassmorphism toggle matching existing sidebar theme

Pass the map ref and toggle state down to FluxMap so it can respect the toggle setting. Alternatively, manage visibility directly in FluxMap via a shared state/prop.

---

## 8. Route Cards: Traffic Badge

**File:** `frontend/components/RouteCards.tsx`

Add a traffic severity badge next to the delay indicator for driving and hybrid routes:

**Condition:** Show when `route.traffic_summary` exists AND `route.mode === "driving" || route.mode === "hybrid"`

**Badge styling by label:**

```typescript
const TRAFFIC_BADGE_STYLE: Record<string, string> = {
  "Light Traffic": "bg-emerald-500/20 text-emerald-400",
  "Moderate Traffic": "bg-amber-500/20 text-amber-400",
  "Heavy Traffic": "bg-orange-500/20 text-orange-400",
  "Severe Traffic": "bg-red-500/20 text-red-400",
};
```

**Display:** Icon (Navigation or AlertTriangle from lucide-react) + short label (strip " Traffic" → just "Light", "Moderate", "Heavy", "Severe")

---

## 9. Decision Matrix: Traffic in Zen

**File:** `frontend/components/DecisionMatrix.tsx`

In the Zen column, when the winning route has a `traffic_summary`:

- Show the traffic label as a small colored subtitle below the existing "% calm" metric
- Color-code by severity:
  - Light → `text-emerald-400`
  - Moderate → `text-amber-400`
  - Heavy → `text-orange-400`
  - Severe → `text-red-400`
- Font size: ~10px, positioned between the main metric and mode label

---

## 10. Congestion Tooltips (NEW)

**File:** `frontend/components/FluxMap.tsx` and/or `frontend/lib/mapUtils.ts`

Add hover tooltips on congestion-colored route segments:

### Implementation

1. **Register mouse events** on congestion sub-segment layers:
   - `mouseenter` → show tooltip, change cursor to `pointer`
   - `mouseleave` → hide tooltip, reset cursor

2. **Tooltip content** based on congestion level:
   | Level | Tooltip Text |
   |-------|-------------|
   | `low` | "Light Traffic — flowing smoothly" |
   | `moderate` | "Moderate Traffic — some slowdowns" |
   | `heavy` | "Heavy Traffic — expect delays" |
   | `severe` | "Severe Traffic — significant delays" |

3. **Tooltip styling:**
   - Use a Mapbox `Popup` or a custom floating div positioned at cursor
   - Dark background (`bg-gray-900/90`), white text, small font
   - Border-left colored by congestion level (using `CONGESTION_COLORS`)
   - No close button, disappears on mouse leave
   - Offset slightly above cursor to avoid flicker

4. **Layer identification:**
   - When creating congestion sub-segment layers in `mapUtils.ts`, store the congestion level as a layer property or use a naming convention (e.g. layer ID contains `-cong-heavy-`)
   - In FluxMap, query hovered layers and extract the congestion level to determine tooltip text

---

## 11. Map Traffic Legend (NEW)

**File:** `frontend/components/FluxMap.tsx` (or a new `TrafficLegend.tsx` component)

Add a small floating legend showing congestion color meanings:

### Layout

```
┌──────────────────────┐
│  Traffic Conditions   │
│  ● Light              │
│  ● Moderate           │
│  ● Heavy              │
│  ● Severe             │
└──────────────────────┘
```

### Implementation

- **Position:** Bottom-left of the map (above Mapbox attribution), or top-right corner
- **Visibility:** Only visible when traffic tileset layer is active (respect the toggle from Step 7b)
- **Style:** Glassmorphism panel (`backdrop-blur-md bg-black/50`), rounded corners, small padding
- **Color dots:** Small colored circles using `CONGESTION_COLORS` values
- **Responsive:** Collapse or hide on mobile viewports if needed

---

## 12. Animated Severe Traffic Pulse (NEW)

**File:** `frontend/lib/mapUtils.ts` and/or `frontend/components/FluxMap.tsx`

Add a subtle pulsing animation on route segments with `severe` congestion:

### Implementation

1. **Identify severe segments:** When drawing congestion sub-segments, flag layers where `congestion === "severe"`

2. **Animation technique — line-dasharray:**
   - Apply a `line-dasharray` paint property to severe congestion layers
   - Use `requestAnimationFrame` or `setInterval` to cycle the dash offset
   - Example dash pattern: `[2, 2]` cycling to `[0, 2, 2, 0]` etc.

   ```typescript
   // In FluxMap useEffect or a dedicated animation hook
   let dashStep = 0;
   const animateSevere = () => {
     dashStep = (dashStep + 1) % 4;
     const dashArray = dashStep % 2 === 0 ? [2, 4] : [4, 2];

     // Find all severe congestion layers
     severeLayerIds.forEach((layerId) => {
       if (map.getLayer(layerId)) {
         map.setPaintProperty(layerId, "line-dasharray", dashArray);
       }
     });

     animationFrameId = requestAnimationFrame(animateSevere);
   };
   ```

3. **Performance:** Only animate if severe segments exist. Cancel animation on cleanup/unmount.

4. **Subtlety:** Keep the animation gentle — slow cycle (~500ms per step), slight dash variation. Should draw attention without being distracting.

---

## 13. Fallback Behavior

| Failure Scenario | Behavior |
|---|---|
| Mapbox returns no `congestion` annotation | Flat single-color driving route (mode color), rush-hour heuristic stress scoring |
| Mapbox API fails entirely | Straight-line geometry with haversine distance, no congestion data |
| Traffic tileset unavailable | Map still renders, just no background traffic layer |
| `congestion_segments` empty on frontend | Falls through to standard single-color segment rendering |
| Browser doesn't support `requestAnimationFrame` | No pulse animation, static rendering |

**Critical rule:** Never show green as the "default" driving route color when there's no congestion data. Use the mode's standard color (blue) or the existing route color. Green should only appear when Mapbox explicitly reports `"low"` congestion.

---

## 14. Verification Checklist

### Backend Verification

```bash
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin":{"lat":43.7804,"lng":-79.4153},"destination":{"lat":43.6453,"lng":-79.3806}}'
```

Check the response:
- [ ] Driving route has `traffic_summary` (e.g. "Moderate Traffic")
- [ ] Driving route segment has `congestion_level` (e.g. "moderate")
- [ ] Driving route segment has `congestion_segments` array with sub-geometries
- [ ] Each sub-segment has `geometry` (GeoJSON LineString) and `congestion` (level string)
- [ ] Hybrid route driving segment also has congestion fields
- [ ] `stress_score` varies based on real traffic data (not just heuristic)

### Frontend Verification

- [ ] Driving route renders as multi-colored segments with dark outline
- [ ] Colors match: green (low), amber (moderate), orange (heavy), red (severe)
- [ ] Mapbox traffic tileset visible as semi-transparent background layer
- [ ] Traffic toggle in sidebar shows/hides traffic tileset
- [ ] Traffic badge appears on driving/hybrid route cards
- [ ] Traffic label shown in Zen column of Decision Matrix
- [ ] Hovering congestion segments shows tooltip with severity description
- [ ] Traffic legend visible when traffic layer is active
- [ ] Severe congestion segments have subtle pulse animation
- [ ] Selecting a route highlights it (thicker outline + segments)

### Fallback Verification

- [ ] Temporarily remove Mapbox token → app still works with heuristic stress
- [ ] Routes without congestion data render as flat single-color (not green)
- [ ] No traffic layer, no traffic badge, no tooltip when data unavailable
- [ ] No console errors when congestion data is missing

---

## Parallelization Strategy

This task has two independent tracks that can run simultaneously:

**Track A (Backend):** Steps 3–4 — Models + route engine + congestion helpers. Pure Python, no frontend dependency.

**Track B (Frontend types):** Step 5 — TypeScript types + constants. Simple additions, no backend dependency.

**Then sequentially:** Steps 6–12 depend on both tracks being done (frontend rendering needs backend data + frontend types).

**Suggested execution:**
1. Launch **Agent 1** for Track A (backend) and **Agent 2** for Track B (frontend types) **in parallel**
2. After both complete, implement Steps 6–12 sequentially
3. Run verification checks
