# Prompt: Phase 1 — Core Functionality Lock-In

**Context:**
You are an expert software engineer working on the FluxRoute project (a multimodal transit app for the GTHA).
Your goal is to execute **Phase 1: Core Functionality Lock-In** from the roadmap.
This phase ensures all existing features work reliably before we integrate complex new data sources in Phase 2.

**Prerequisites:**
- Ensure you are in the project root: `/Users/bryan/Documents/hackathons/fluxRoute/CTRLHACKDEL-Fluxroute`
- Ensure the virtual environment is active (if running commands manually).
- **Critical:** The git working directory should be clean. (Note: You may have local changes to `CLAUDE.md` and `README.md`. Stash or commit them if necessary before starting complex work).

---

## 1. Backend Stability

**Goal:** Ensure the backend is stable, the ML model is trained, and all endpoints are functional.

**Steps:**

1.  **Train the XGBoost Model:**
    -   Navigate to backend: `cd backend`
    -   Run the training script: `python3 -m ml.train_model`
    -   **Verify:** Check that `backend/ml/delay_model.joblib` has been created.

2.  **Restart & Verify Backend:**
    -   Start the backend: `python3 -m uvicorn app.main:app --reload` (in a separate terminal or background)
    -   **Verify Logs:** Look for "Loaded XGBoost model" in the startup logs to confirm ML mode is active.

3.  **Test Endpoints (in another terminal):**
    -   **Delay Prediction:**
        ```bash
        curl "http://localhost:8000/api/predict-delay?line=Line+1&hour=8&day_of_week=0"
        ```
        Expect a JSON response with `delay_probability` and `expected_delay_minutes`.
    -   **Weather:**
        ```bash
        curl http://localhost:8000/api/weather
        ```
        Expect real weather data for Toronto.
    -   **Route Generation:**
        Ask Gemini (or use the frontend) to generate a route. Verify the response includes `delay_info` populated by the ML model.

4.  **Verify Gemini Integration:**
    -   Ask the chat assistant: "What's the fastest route from Union Station to Finch?"
    -   **Verify:** The assistant should use tools (e.g., `get_routes`) and provide a relevant answer.

---

## 2. Frontend Stability

**Goal:** Verify the UI is functional and visual elements are correct.

**Steps:**

1.  **Start Frontend:**
    -   Navigate to frontend: `cd frontend`
    -   Run: `npm run dev`
    -   Open `http://localhost:3000`

2.  **Visual Verification Checklist:**
    -   [ ] **Route Cards:** Check duration, cost, delay badge, and summary are visible.
    -   [ ] **Decision Matrix:** Verify "Fastest", "Thrifty", and "Zen" labels appear on the correct cards.
    -   [ ] **Cost Breakdown:** Click to expand. Verify fare, gas, and parking costs are shown.
    -   [ ] **Delay Indicator:** Verify color coding (Green <30%, Yellow 30-60%, Red >60%).
    -   [ ] **Live Alerts:** Check the banner at the top rotates through alerts.
    -   [ ] **Map Markers:** Verify vehicle markers (even mock ones) appear on the map.
    -   [ ] **Map Highlight:** Click a route card. Verify the route polyline on the map is highlighted.
    -   [ ] **Sidebar:** Test collapsing and expanding the sidebar on different window sizes.

---

## 3. Bug Hunt

**Goal:** Identify and fix common issues.

**Steps:**

1.  **Console/Terminal Checks:**
    -   Check browser console (F12) for any red JavaScript errors.
    -   Check backend terminal for any Python traceback exceptions.

2.  **Route Testing:**
    -   **Standard:** Downtown to Uptown (e.g., Union to Yorkdale).
    -   **Short Distance:** Origin and Destination very close (e.g., 200m apart). 
    -   **Long Distance:** Across GTHA (e.g., Oshawa to Burlington).
    -   **Verify:** No crashes, reasonable routes generated.

3.  **Network:**
    -   Check the "Network" tab in browser dev tools.
    -   **Verify:** No CORS errors (red failed requests) when frontend calls backend.

---

**Completion Criteria:**
-   [ ] `delay_model.joblib` exists.
-   [ ] "Loaded XGBoost model" confirmed in logs.
-   [ ] All frontend UI elements (cards, matrix, map) verified.
-   [ ] No critical console/terminal errors.

**Action:**
Please execute these steps one by one. If you encounter an error (e.g., model training fails, frontend crash), **STOP**, fix the issue, and then proceed. Document any fixes made.
