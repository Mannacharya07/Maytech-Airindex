# AIRINDEX — SIH26056
## Execution Report: Smit — Member 2, Data / Index Engineer

> **Team Mantra:** *"Don't find the cheapest flight. Measure how the price of flying is changing."*
> Yours is arguably the most mathematically important role on the team. Mann hands you raw-ish fare observations; you hand the rest of the team a number that a government statistician could defend. Everything the dashboard shows — the headline index, the route cards, the "why did it change" screen — is downstream of the math you write.

---

## 1. Your Mission

Turn fare observations into an actual **Airfare Price Index**. That means: cleaning and validating what Mann's connectors send you, deciding which observations are comparable to each other, computing price relatives, aggregating them into a route-level index using the Jevons method, weighting routes by importance, and rolling it all up into one national number.

You sit here in the pipeline:

```
Member 1 — Collector
        ↓
   FareObservation
        ↓
[ YOU — NORMALIZATION + INDEX ENGINE ]
        ↓
   Index Values + Clean Data
        ↓
Member 3 — Database + API
        ↓
Member 4 — Analytics (lead-time, anomalies, contributions)
        ↓
Member 5 — Government Dashboard
```

---

## 2. The Golden Rule for Your Role

**You are not trying to find "the one correct airfare."** There isn't one — the same route has a different real price for every combination of date, carrier, and booking window. Your job is to construct a *representative measure of price movement* from many comparable observations:

```
Many dynamic prices → Comparable observations → Price relatives → Weighted aggregation → Airfare Price Index
```

If a teammate (or a judge) asks "why isn't this just an average of ticket prices," this is your answer, and it's the whole reason a proper index methodology exists.

---

## 3. The Two Contracts

### 3.1 Input Contract — what you receive from Mann

Every observation arriving from any connector (`live`, `replay`, `synthetic`) looks like this. Confirm this with Mann in the Hour 0–2 freeze — do not let it drift.

```json
{
  "source": "synthetic",
  "data_status": "SYNTHETIC",
  "origin": "DEL",
  "destination": "BOM",
  "carrier": "INDIGO",
  "travel_date": "2026-09-25",
  "observed_at": "2026-09-10T10:00:00",
  "booking_window": "T+15",
  "fare_class": "ECONOMY",
  "base_fare": 4200,
  "taxes": 650,
  "fees": 100,
  "total_fare": 4950,
  "availability": 5
}
```

### 3.2 Output Contract — what you hand to Rakesh's Member 3 (Backend)

Agree this shape with Member 3 during the freeze so their `index_values` table and your output line up exactly.

```json
{
  "date": "2026-09-10",
  "route": "DEL-BOM",
  "booking_window": "T+7",
  "index_value": 117.4
}
```

Decide with Member 3 how you'll represent the **national** number — e.g. a reserved `route` value like `"NATIONAL"`, or a separate flag. Pick one in the freeze meeting and don't revisit it later.

---

## 4. What You're Building — 7 Tasks

### Task 1 — Canonical Fare Model

A typed representation of the `FareObservation` contract (e.g. a `dataclass` or `pydantic` model) that the rest of your engine works with internally, instead of raw dicts. This is what makes Tasks 2–7 clean to write.

### Task 2 — Data Validation

Before anything touches the index calculation, reject or flag:
- Invalid route (not in the agreed representative basket)
- Invalid or unparseable date
- Invalid fare (zero, negative, or absurdly out of range)
- Duplicate observations (see identity key below)
- Missing critical fields
- A `booking_window` outside the agreed set (`T+1, T+7, T+15, T+30, T+45`)

**Acceptance criteria:** garbage in never becomes garbage in the index. Bad rows are rejected with a reason, not silently averaged in.

### Task 3 — Fare Identity (Matching)

Two observations are only comparable if they share the same:

```
origin + destination + carrier + booking_window + fare_class
```

Example identity: `DEL-BOM | INDIGO | T+7 | ECONOMY`

This key is what lets you compare "the same kind of ticket" across two points in time, instead of comparing a Monday IndiGo T+7 fare to a Tuesday Air India T+1 fare (which the blueprint explicitly calls out as *not* equivalent).

### Task 4 — Price Relative

```
Price Relative = Current Price / Base Price
```
Example: ₹5,500 / ₹5,000 = 1.10 → a +10% movement for that one matched pair.

### Task 5 — Jevons Index (elementary aggregation)

For a group of matched observations (same route + booking window, e.g. across carriers), aggregate their price relatives with a **geometric mean**, not an arithmetic one — this is what "Jevons" means and it's the correct way to combine multiplicative price movements:

```
Route/window index = 100 × geometric_mean(price_relative_1, price_relative_2, ..., price_relative_n)
```

Base period is always defined as index = 100.

### Task 6 — Route Weighting

Not every route matters equally. Weight the representative basket (e.g. `DEL-BOM`, `DEL-BLR`, `BOM-BLR`, `DEL-CCU`, `BLR-HYD`, `MAA-DEL`) by approximate passenger-traffic share, referencing DGCA-style traffic patterns. **Document your source/assumption for every weight — never hard-code an unexplained number.** Weights must sum to 1.

### Task 7 — National Index

```
Observation → Price Relative → Route-level Index (geometric) → Route Weight → National Airfare Index (weighted aggregation)
```

This two-stage design (geometric mean *within* a route/window, weighted arithmetic *across* routes) mirrors how real consumer price indices are built, and it's a strong answer if a judge probes your methodology.

---

## 5. Priority Matrix

| MUST HAVE | DO NOT ATTEMPT |
|---|---|
| Canonical schema / typed model | 10 different index methodologies |
| Matching / fare identity logic | Deep learning for index calculation |
| Price relatives | Complex econometrics |
| Jevons index | |
| Route weighting | |
| National index | |

If time is short: a correct national index for **one day** beats an incomplete 30-day trend across ten methodologies.

---

## 6. Your Hour-by-Hour Track

| Hours | What You Do | Deliverable |
|---|---|---|
| 0–2 | **All-team freeze:** confirm the input contract with Mann, the output contract with Member 3, routes, booking windows, and that Jevons is the agreed methodology. | Signed-off contracts |
| 2–6 | Build the Jevons engine: canonical model, price relative, geometric-mean aggregation | Working index calc on synthetic data |
| 6–10 | Route weighting + national index aggregation | End-to-end route → national number |
| 10 | **First integration checkpoint** — your index values need to actually reach Member 3's database and come back out through an API. Fix the join before adding anything new. | Collector → You → DB → API → Dashboard alive |
| 10–14 | Index validation: sanity-check outputs, handle missing-route edge cases, confirm base period = 100 exactly | Hardened, trustworthy index engine |
| 14–18 | Support Member 4: expose per-route, per-window price relatives and index components so they can build "why did the index change?" and anomaly detection on top of your numbers | Route/window-level breakdown available, not just the national figure |
| 18–22 | Support the DGCA back-test (owned by Member 4) with clean historical index values; write up your methodology for `docs/methodology.md` — this becomes your jury defense document | Methodology write-up, validation-ready data |
| 22–26 | Polish: precision/rounding rules, graceful handling of a route with no fresh data that day, clear error messages if the pipeline is fed bad data | Stable index engine |
| 26–28 | **Feature freeze.** Re-run the full pipeline repeatedly, confirm the index is reproducible from the same inputs. | Verified, reproducible demo run |
| 28–30 | Jury prep — you'll get the hardest methodology questions. Know your answers cold (Section 11). | Talking points ready |

---

## 7. Deliverable File Structure

```
index_engine/
├── normalization.py
├── validation.py
├── matching.py
├── price_relative.py
├── jevons.py
├── weights.py
└── national_index.py
```

At minimum, expose data ready for these API endpoints (built by Member 3, fed by you):
- `GET /api/index/current`
- `GET /api/index/history`
- `GET /api/routes/{route}`

---

## 8. Definition of Done

> "Given observations, my engine produces a reproducible route and national Airfare Index."

Checklist:
- [ ] Canonical model matches Mann's contract exactly
- [ ] Validation rejects bad observations with a clear reason, doesn't silently pass them through
- [ ] Fare identity correctly groups only truly comparable observations
- [ ] Price relative computed correctly for every matched pair
- [ ] Jevons (geometric mean) used for elementary aggregation — not a plain average
- [ ] Route weights sum to 1 and are documented, not arbitrary
- [ ] National index reproduces the same value given the same input twice
- [ ] Base period always evaluates to exactly 100
- [ ] Output matches the agreed `index_values` contract for Member 3

---

## 9. Using AI Tools to Move Fast

Paste both contracts (Section 3) into every prompt so the AI's output actually plugs into the rest of the pipeline. Treat AI output as a first draft of the *code*, but you own the *math* — always sanity-check a small hand-calculated example (like the ₹5,500/₹5,000 = 1.10 example) against what the generated function returns before trusting it.

### Prompt templates you can copy-paste

**(a) Canonical model + validation**
```
Build a Python (pydantic or dataclass) model called FareObservation matching this
exact schema: <paste input contract from 3.1>. Then write a function
validate_observation(obs) -> tuple[bool, str] that rejects observations with:
invalid/unparseable travel_date, base_fare/taxes/fees/total_fare <= 0,
booking_window not in {T+1,T+7,T+15,T+30,T+45}, or any missing required field.
Return (False, reason) on rejection, (True, "") on success.
```

**(b) Matching / fare identity**
```
Write a function fare_identity(obs: FareObservation) -> str that returns a stable
identity key built from origin, destination, carrier, booking_window, and
fare_class, e.g. "DEL-BOM|INDIGO|T+7|ECONOMY". Then write
find_matched_pairs(observations: list[FareObservation], base_date, current_date)
that groups observations by identity and returns, for each identity present in
both periods, the (base_observation, current_observation) pair.
```

**(c) Price relative + Jevons**
```
Write price_relative(base_obs, current_obs) -> float returning
current_obs.total_fare / base_obs.total_fare. Then write
jevons_index(price_relatives: list[float]) -> float that returns 100 times the
geometric mean of the given price relatives (use scipy.stats.gmean or implement
manually with logs to avoid overflow on many observations). Include a docstring
explaining why geometric mean is used instead of arithmetic mean for price
relatives.
```

**(d) Route weighting + national index**
```
I have route-level Jevons indices for a representative basket of Indian domestic
routes (DEL-BOM, DEL-BLR, BOM-BLR, DEL-CCU, BLR-HYD, MAA-DEL). Write a function
national_index(route_indices: dict[str, float], route_weights: dict[str, float])
-> float that computes a weighted arithmetic average, validating that weights sum
to 1.0 (raise a clear error if not). Also write a helper that loads weights from a
simple CSV/config file rather than hard-coding them, so the weighting assumptions
are visible and editable in one place.
```

**(e) Output formatting + reproducibility test**
```
Write a pytest test that runs my national_index and jevons_index functions twice
on the same fixed input and asserts the outputs are identical (reproducibility),
and a second test asserting that when every price relative equals 1.0, the
resulting index is exactly 100. Also write a formatter that converts computed
route/national index values into this exact output schema:
<paste output contract from 3.2>
```

---

## 10. Common Pitfalls

- **Using a plain average instead of a geometric mean** — this is the single most likely thing a judge will probe (see Q1/Q2 below). Get this right.
- **Comparing non-comparable observations** — e.g. matching a Monday IndiGo fare to a Tuesday Air India fare just because it's the "same route." Always match on the full identity key.
- **Weights that don't sum to 1**, or that are picked with no stated rationale — document them even if they're an approximation for the prototype.
- **Forgetting the base period must equal exactly 100** — a small rounding slip here undermines trust in every number downstream.
- **Silently dropping missing-route days** — decide (and document) whether a missing route that day is excluded, carried forward, or reweighted. Any of these is defensible; *not deciding* is not.
- **Duplicate observations inflating a route's weight in practice** — rely on Mann's `source`+identity+timestamp to de-duplicate before aggregating.

---

## 11. Jury Q&A You Should Own

**Q: Why not just take the average ticket price?**
> Because airfare observations are heterogeneous and dynamic. We need comparable observations and relative price movements, not a simple average of unrelated fares.

**Q: Why are you using Jevons specifically?**
> Jevons aggregates price relatives geometrically, which is the statistically correct way to combine multiplicative price movements across comparable observations. It also gives a transparent, reproducible methodology appropriate for a prototype.

**Q: Why these six routes and these weights?**
> We use a representative route basket informed by passenger-traffic patterns rather than treating every route equally — the weights are documented in our methodology notes, not arbitrary.

**Q: Is your index the official CPI?**
> No — this is a prototype methodology intended to support airfare price measurement. We don't claim it replaces the official CPI methodology.

---

## 12. Quick Reference

- **Your one-line done-condition:** *"Given observations, my engine produces a reproducible route and national Airfare Index."*
- **Your non-negotiables:** geometric mean for price relatives (Jevons), documented weights summing to 1, base period always = 100, reproducible output.
- **Your safety net:** if time runs short, a correct index for one route on one day, computed properly, beats a flashy dashboard fed by a wrong formula.
