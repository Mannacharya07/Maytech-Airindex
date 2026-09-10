# AIRINDEX — SIH26056
## Execution Report: Aditya — Member 4, Analytics + Intelligence Engineer

> **Team Mantra:** *"Don't find the cheapest flight. Measure how the price of flying is changing."*
> Mann collects data, Smit turns it into a number, Mihir stores and serves it. Your job is to make that number *mean something* to a judge — why it moved, what's unusual about it, and how the price actually behaves as travel gets closer. Without your layer, AirIndex is "a scraper plus a calculator." With it, it's a genuine intelligence product.

---

## 1. Your Mission

Convert the raw index into meaningful intelligence: how fares behave as booking windows shorten (lead-time analysis), what looks unusual (anomaly detection), whether pricing behaviour has structurally shifted (change detection — bonus), which routes and windows are driving any given index movement (contribution analysis), and whether the whole thing is even close to reality (validation against a reference series). This is the layer that turns a dashboard from "here's a number" into "here's why, and here's how confident we are."

You sit here in the pipeline:

```
Member 3 (Mihir) — REST API + PostgreSQL
        ↓
[ YOU — ANALYTICS / INTELLIGENCE ENGINE ]
        ↓  Lead-Time, Anomaly, Contribution, Validation
Member 5 — Government Dashboard
        ↓
FINAL DEMO
```

---

## 2. The Contracts You Sit Between

### 2.1 What you pull in

Fare observations and index values, via Mihir's API (`/api/fares`, `/api/index/current`, `/api/index/history`) or direct DB access if the team agrees that's faster for internal (non-frontend) consumers. **Confirm this choice with Mihir explicitly** — don't assume.

### 2.2 What you hand back — three output shapes to agree on

**Lead-time output** (feeds `/api/lead-time` and the lead-time graph):
```json
{
  "route": "DEL-BOM",
  "curve": {
    "T+45": 4100,
    "T+30": 4400,
    "T+15": 4900,
    "T+7": 5700,
    "T+1": 7300
  }
}
```

**Anomaly record** (feeds `/api/anomalies`):
```json
{
  "route": "DEL-BOM",
  "booking_window": "T+1",
  "severity": "HIGH",
  "change_pct": 31,
  "detected_at": "2026-09-10T10:00:00",
  "reason": "Fare rose sharply relative to recent baseline"
}
```

**Explanation object** (feeds `/api/contributors`, and directly powers the "Why did the index change?" screen):
```json
{
  "index_change": 4.2,
  "top_routes": [
    { "route": "DEL-BOM", "contribution": 1.8 },
    { "route": "DEL-BLR", "contribution": 1.2 }
  ],
  "top_windows": [
    { "window": "T+1", "contribution": 1.1 },
    { "window": "T+7", "contribution": 0.7 }
  ]
}
```

**Also confirm with Mihir** whether you write these into the database yourself (using models he exposes) or hand them back as return values for him to persist. Pick one in the freeze meeting, not during integration.

---

## 3. What You're Building — 7 Tasks

### Task 1 — Lead-Time Analysis
For each route, compute the average fare at each booking window: `T+45, T+30, T+15, T+7, T+1`. This is the data proof of the project's central claim — that airfare is dynamic and lead-time-dependent.

### Task 2 — Lead-Time Curve
Package Task 1's output as "Fare vs Days Before Travel" — this becomes one of the main dashboard graphs.

### Task 3 — Anomaly Detection
Flag unusual fare movement, e.g. a jump from a stable ~₹4,500–4,700 range to ₹9,800. Output should include route, booking window, severity, and the percentage change. **Use one practical method — do not spend the whole hackathon building an advanced ML model.** A rolling robust z-score (median + MAD) is enough for this MVP.

### Task 4 — Change Detection (optional but recommended)
Detect when the underlying price series has undergone a sustained regime shift, not just a single spike — e.g. "potential pricing regime change detected around this date." A lightweight method like CUSUM is sufficient; this is explicitly a bonus, not core.

### Task 5 — Contribution Analysis
The most important explainability feature. If the national index moved from `112.7 → 117.4`, calculate which routes and which booking windows drove that movement, e.g. `DEL-BOM +1.8`, `T+1 +1.1`. This is what lets a government user answer "what caused this?" instead of just seeing a number change.

### Task 6 — Explanation Object
Package Task 5's output into the exact JSON shape in Section 2.2 so Member 5's frontend can render it directly without further transformation on their end.

### Task 7 — Validation
If reference data is available, compare AirIndex against it and compute **actual** MAE, RMSE, MAPE, and correlation. **Never hard-code or invent these numbers** — they must come from a real calculation against real (or realistic historical/replay) reference values.

---

## 4. Priority Matrix

| MUST | SHOULD | BONUS |
|---|---|---|
| Lead-time analysis | Anomaly detection | Change-point detection |
| Contribution analysis | | Advanced forecasting |

**Avoid entirely:**
- Isolation Forest, deep learning, or any heavy ML pipeline for anomaly detection — one practical statistical method is the correct scope here.
- Building multiple competing anomaly or change-point algorithms "to compare" — pick one and make it solid.
- Treating every high fare as automatically wrong data and discarding it (see Section 8).
- Fabricating validation metrics that "look plausible" — this is explicitly forbidden and is exactly the kind of thing a sharp judge will probe.

---

## 5. Your Hour-by-Hour Track

| Hours | What You Do | Deliverable |
|---|---|---|
| 0–2 | **All-team freeze:** confirm booking windows, routes, schema, and — specifically — the three output shapes in Section 2.2 with Mihir and Smit. | Agreed output contracts |
| 2–6 | Build lead-time calculation | Working `lead_time_curve()` on synthetic data |
| 6–10 | Build contribution analysis | Working `explain_index_change()` producing a consistent breakdown |
| 10 | **First integration checkpoint** — your lead-time and contribution outputs need to actually reach Mihir's DB/API and Member 5's dashboard. If it doesn't connect end-to-end, stop adding features and fix the join. | Real analytics output flowing through the whole pipeline once |
| 10–14 | Build anomaly detection (robust z-score / rolling threshold — one method, done well) | Working `detect_anomalies()` |
| 14–18 | Finish integrating contribution analysis into the "Why did the index change?" screen with Member 5; finalize anomaly severity thresholds | Explainability screen backed by real data |
| 18–22 | Build validation: compute actual MAE/RMSE/MAPE/correlation against reference data; contribute to methodology documentation | Real validation numbers, documented method |
| 22–26 | Polish: clear severity labels, sensible thresholds (not flagging every normal fluctuation as an anomaly), clean explanation-object formatting | Demo-ready analytics layer |
| 26–28 | **Feature freeze.** Re-run the pipeline and confirm your outputs stay consistent and sane across repeated runs. | Verified stable demo run |
| 28–30 | Jury prep — you'll likely get asked how you tell a real anomaly from a legitimate price spike, and how you know your index is accurate. | Talking points ready |

---

## 6. Deliverable File Structure

```
analytics/
├── lead_time.py
├── anomaly.py
├── changepoint.py
├── contributions.py
└── validation.py
```

---

## 7. Definition of Done

> "I can explain how lead time and route-level movements affect the index."

Checklist:
- [ ] Lead-time curve computed correctly per route, matching the agreed output shape
- [ ] Contribution analysis produces per-route and per-window contributions that plausibly sum back to the total index change
- [ ] Explanation object matches the exact schema Member 5 expects
- [ ] Anomaly detection uses one clear, defensible method (not several half-built ones)
- [ ] Anomalies are flagged for review, not silently discarded as "bad data"
- [ ] Validation metrics (MAE/RMSE/MAPE/correlation) are computed from real data, never hard-coded
- [ ] (Bonus) Change-point detection, if built, uses one lightweight, explainable method

---

## 8. A Warning Worth Repeating

> **Outlier ≠ automatically wrong data.**

A ₹10,000 fare during a festival period next to a normal ₹5,000 baseline can be a *real, legitimate* market observation — not a scraping error. Your anomaly detector's job is to **flag** unusual movement for visibility, not to silently delete anything that looks high. Build your severity levels and reasoning around this distinction; it's a detail judges specifically listen for.

---

## 9. Using AI Tools to Move Fast

Paste the output shapes in Section 2.2 into every prompt so what you generate plugs directly into Mihir's API and Member 5's dashboard without a translation step. For anomaly and change-point detection specifically, ask the AI to keep the method simple and explain *why* a given threshold or statistic was chosen — you'll need that explanation for the jury regardless of who wrote the code.

### Prompt templates you can copy-paste

**(a) Lead-time analysis**
```
Write a Python function lead_time_curve(route: str, observations: list[dict]) ->
dict that groups fare observations for a given route by booking_window
(T+1, T+7, T+15, T+30, T+45), computes the average total_fare for each window
from the most recent matching observations, and returns a dict like
{"T+45": 4100, "T+30": 4400, "T+15": 4900, "T+7": 5700, "T+1": 7300} ready to
be charted as fare vs. days before travel.
```

**(b) Anomaly detection**
```
Write a Python function detect_anomalies(fare_series: list[float], route: str,
booking_window: str) -> list[dict] that flags unusual fare movements using a
robust z-score (median + median absolute deviation) over a rolling window, so
that a single legitimate high-demand spike isn't automatically treated as an
error — it should still be flagged for visibility, not discarded. Return a list
of dicts shaped like {"route": ..., "booking_window": ..., "severity":
"HIGH"/"MEDIUM"/"LOW", "change_pct": ..., "detected_at": ..., "reason": ...}.
Use one practical statistical method only — do not implement Isolation Forest
or any ML pipeline for this.
```

**(c) Change-point detection (bonus)**
```
Write a lightweight CUSUM-based change-point detector in Python that takes a
time-ordered list of index values for a route and flags the approximate date
where a sustained shift in level occurred (not just a single-point spike).
Return {"route": ..., "change_detected_at": ..., "description": "Potential
pricing regime change detected"}. Keep this simple — it's a bonus feature for
a 30-hour hackathon, not a research implementation.
```

**(d) Contribution analysis + explanation object**
```
Write a Python function explain_index_change(previous_index, current_index,
route_indices_prev: dict, route_indices_curr: dict, route_weights: dict,
window_indices_prev: dict, window_indices_curr: dict) -> dict that decomposes
the total index change into per-route and per-booking-window contributions
(each proportional to that route's/window's weighted change), ranks them by
magnitude, and returns exactly this shape:
{"index_change": 4.2,
 "top_routes": [{"route": "DEL-BOM", "contribution": 1.8}, ...],
 "top_windows": [{"window": "T+1", "contribution": 1.1}, ...]}
Add a short comment explaining why the contributions should approximately sum
back to the total index_change.
```

**(e) Validation metrics**
```
Write a Python function validate_against_reference(airindex_values: list[float],
reference_values: list[float]) -> dict that computes real MAE, RMSE, MAPE, and
Pearson correlation between our computed index series and a reference series of
matching dates/length. Return {"mae": ..., "rmse": ..., "mape": ...,
"correlation": ...}. These must be actual calculated numbers from the input
arrays — never hard-code or fabricate a plausible-looking result.
```

---

## 10. Common Pitfalls

- **Building a heavy ML anomaly detector** when a simple robust statistical method would do the job in a fraction of the time — this is explicitly out of scope for the MVP.
- **Auto-deleting high-fare observations** as if they were errors — some are real (festivals, demand spikes). Flag, don't erase.
- **Contribution numbers that don't roughly reconcile** with the total index change — a judge who does the arithmetic in their head will notice.
- **Hard-coding or "estimating" validation metrics** to look good — this is called out explicitly in the blueprint as something to never do, and it's the fastest way to lose credibility if discovered.
- **Building three different anomaly/change-point methods "to be safe"** instead of committing to one well-explained approach — depth beats breadth here.
- **Not documenting your thresholds** — if you can't explain *why* a movement counted as HIGH severity versus LOW, you'll struggle in Q&A.

---

## 11. Jury Q&A You Should Own

**Q: How do you know your index is correct?**
> We validate the prototype against independent official reference airfare data using a historical back-test, and we report objective error and correlation metrics — not a hand-picked or invented number.

**Q: How do you tell a real anomaly from a legitimate price spike (like a festival)?**
> An outlier isn't automatically wrong data — a genuine demand spike can produce a real high fare. Our anomaly detection flags unusual movement for visibility and review rather than silently discarding it, and severity is based on statistical deviation from a route's recent baseline, not a fixed price ceiling.

---

## 12. Quick Reference

- **Your one-line done-condition:** *"I can explain how lead time and route-level movements affect the index."*
- **Your non-negotiables:** contribution numbers that reconcile with the total change, anomalies flagged not deleted, validation metrics that are always real calculations.
- **Your safety net:** lead-time analysis and contribution analysis are MUST-have — if time runs out, anomaly detection and change-point detection are the first things to trim, in that order.
