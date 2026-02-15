# FluxRoute Landing Page — Implementation Plan

## Goal
Create an animated landing/front page with a Toronto skyline background, moving train and subway, and a call-to-action button that navigates to the map app.

---

## Visual Concept

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│                                                                  │
│              ✦  F L U X R O U T E  ✦                            │
│                                                                  │
│         AI-Powered Multimodal Transit Routing                    │
│              for the Greater Toronto Area                        │
│                                                                  │
│            ┌──────────────────────────┐                          │
│            │   Start Your Journey →   │  ← CTA Button           │
│            └──────────────────────────┘                          │
│                                                                  │
│   ───────── Toronto Skyline (CSS/SVG) ──────────                │
│   🏢  🏙️  CN Tower  🏢  🏢  🏙️  🏢                            │
│                                                                  │
│  ═══🚆════════════════════════════════►  ← Train (animated)     │
│  ◄════════════════════════════🚇═══════  ← Subway (animated)    │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  ← Ground/tracks       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Restructure Next.js Routing

**Why:** Currently `page.tsx` is the map app. We need the landing page at `/` and the map at `/map`.

**Changes:**
- Move current `frontend/app/page.tsx` → `frontend/app/map/page.tsx` (the map app)
- Create new `frontend/app/page.tsx` (landing page)
- No layout changes needed — both pages share the root layout

**Files:**
- `frontend/app/map/page.tsx` — existing map app (moved)
- `frontend/app/page.tsx` — new landing page

---

### Step 2: Create the Landing Page Component

**File:** `frontend/app/page.tsx`

**Structure:**
```tsx
// Full-viewport landing page
<div className="relative w-screen h-screen overflow-hidden bg-[#0a0f1c]">

  {/* Background: dark gradient sky */}
  <div className="absolute inset-0 bg-gradient-to-b from-[#0a0f1c] via-[#111827] to-[#1a1a2e]" />

  {/* Animated stars/particles (subtle) */}
  <div className="stars" />

  {/* Toronto Skyline — CSS/SVG silhouette at bottom */}
  <SkylineSVG />

  {/* Animated Train — moves left-to-right, loops */}
  <TrainAnimation />

  {/* Animated Subway — moves right-to-left, below train */}
  <SubwayAnimation />

  {/* Ground/tracks strip */}
  <div className="absolute bottom-0 w-full h-16 bg-[#1a1a2e]" />

  {/* Hero Content — centered text + CTA */}
  <div className="relative z-10 flex flex-col items-center justify-center h-full">
    <h1>FluxRoute</h1>
    <p>AI-Powered Multimodal Transit for the GTA</p>
    <Link href="/map">
      <button>Start Your Journey →</button>
    </Link>
  </div>
</div>
```

---

### Step 3: Build the Toronto Skyline (Inline SVG)

**Approach:** Pure CSS/SVG silhouette of the Toronto skyline (no external images needed).

**Elements (SVG shapes):**
- CN Tower (tall narrow triangle with observation deck bulge)
- Rogers Centre dome
- Various skyscrapers (rectangles with different heights)
- Subtle window lights (small glowing dots)

**Styling:**
- Dark silhouette (`fill: #1e293b`) against the gradient sky
- Subtle glow at the base of buildings
- Positioned at `bottom: 80px` (above the train tracks)

---

### Step 4: Animate the Train (CSS Keyframes)

**Approach:** SVG or CSS-drawn GO Train that scrolls horizontally.

**Train Design (CSS/SVG):**
- Green-and-white GO Train (matches the reference image)
- Simplified side-view: rectangular body, windows, wheels
- Approximately 200-300px wide

**Animation:**
```css
@keyframes trainMove {
  0%   { transform: translateX(-350px); }
  100% { transform: translateX(calc(100vw + 350px)); }
}

.train {
  animation: trainMove 12s linear infinite;
  position: absolute;
  bottom: 80px; /* on the tracks */
}
```

- Train enters from the left, exits right, loops infinitely
- Duration: ~12 seconds for a smooth, not-too-fast feel
- Positioned on the "upper track" layer

---

### Step 5: Animate the Subway (CSS Keyframes)

**Approach:** Similar to train but different design, moving in opposite direction.

**Subway Design (CSS/SVG):**
- TTC-style red/silver subway car
- Slightly smaller than the train
- Different window pattern

**Animation:**
```css
@keyframes subwayMove {
  0%   { transform: translateX(calc(100vw + 300px)); }
  100% { transform: translateX(-300px); }
}

.subway {
  animation: subwayMove 15s linear infinite;
  animation-delay: 3s; /* offset from train */
  position: absolute;
  bottom: 40px; /* lower track */
}
```

- Subway enters from the right, exits left (opposite direction to train)
- Slightly slower speed (15s) for visual variety
- 3-second delay so they don't overlap at start

---

### Step 6: Hero Content & CTA Button

**Content:**
```
FluxRoute
AI-Powered Multimodal Transit Routing
for the Greater Toronto Area

[Start Your Journey →]
```

**Styling:**
- Title: Large bold text with subtle gradient or glow effect
- Subtitle: Lighter weight, muted color
- CTA Button:
  - Glass-morphism style (matches app theme)
  - Hover: subtle glow + scale effect
  - Uses Next.js `<Link href="/map">` for client-side navigation

**Bonus interactions:**
- Title fades in on load (CSS animation, 0.5s delay)
- Subtitle fades in after title (1s delay)
- CTA button fades in last (1.5s delay)
- Subtle parallax on mouse move (optional — keep simple)

---

### Step 7: Add CSS Animations to `globals.css`

**New animations to add:**
```css
/* Train movement */
@keyframes trainMove { ... }
@keyframes subwayMove { ... }

/* Hero text fade-in */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Subtle star twinkle (optional) */
@keyframes twinkle {
  0%, 100% { opacity: 0.3; }
  50%      { opacity: 1; }
}

/* CTA button glow pulse */
@keyframes glowPulse {
  0%, 100% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
  50%      { box-shadow: 0 0 40px rgba(59, 130, 246, 0.6); }
}
```

---

### Step 8: Update `globals.css` for Landing Page

**Changes:**
- Remove `overflow: hidden` from `body` (or make it conditional) — the landing page needs full viewport but the map page still needs overflow hidden
- Add the new keyframe animations
- The landing page will set its own overflow on its container

---

## File Summary

| File | Action | Description |
|------|--------|-------------|
| `frontend/app/page.tsx` | **Replace** | New landing page with skyline + animations |
| `frontend/app/map/page.tsx` | **Create** (move) | Existing map app moved here |
| `frontend/app/globals.css` | **Edit** | Add keyframe animations for train/subway/fadeIn |
| `frontend/tailwind.config.ts` | **Edit** | Add custom animation utilities (optional) |

---

## Design Details

### Color Palette (matching existing dark theme)
- Sky gradient: `#0a0f1c` → `#111827` → `#1a1a2e`
- Skyline silhouette: `#1e293b`
- Building window lights: `#fbbf24` (warm yellow, small dots)
- CN Tower beacon: `#ef4444` (red pulse)
- Train body: `#22c55e` (GO green) + `#f5f5f5` (white)
- Subway body: `#ef4444` (TTC red) + `#d4d4d8` (silver)
- CTA button: `#3b82f6` (accent blue) with glass effect
- Text: `#f0f0f0` (primary), `#94a3b8` (secondary)

### Responsive Considerations
- Skyline and trains scale with viewport width
- Text sizes responsive (clamp or breakpoints)
- On mobile: trains slightly smaller, animation speed adjusted
- CTA button full-width on small screens

### Performance Notes
- All animations are CSS-only (GPU-accelerated transforms)
- No JavaScript animation libraries needed
- SVGs are inline (no network requests)
- Landing page is lightweight — fast initial load

---

## User Flow

```
Landing Page (/)
    │
    │  Click "Start Your Journey →"
    │
    ▼
Map App (/map)
    │
    │  (Full existing FluxRoute app)
    │
    └── Route search, AI chat, live alerts, etc.
```

---

## Waiting On
- **Second subway image** from user — will refine the subway SVG design based on the reference image provided later
- For now, will implement with a generic TTC-style subway car design that can be updated

---

## Notes
- The landing page is a **static page** — no API calls, no data fetching
- Train and subway are **pure CSS/SVG animations** — no canvas, no JS animation
- The page should feel polished but simple — it's a hackathon demo entry point
- Keep the whole implementation in 2-3 files max
