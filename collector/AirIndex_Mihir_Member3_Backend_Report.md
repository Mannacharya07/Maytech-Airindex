# AIRINDEX — SIH26056
## Execution Report: Mihir Patel — Member 3, Backend + Database Engineer

> **Team Mantra:** *"Don't find the cheapest flight. Measure how the price of flying is changing."*
> You're not the flashiest role and you're not the mathematical core — but nothing works without you. Mann's connectors, Smit's index engine, the analytics, and the dashboard are five separate pieces of code until you wire them into one reliable system. **Backend is the bridge.**

---

## 1. Your Mission

Connect every other module into one reliable, queryable system: store what Mann collects and Smit computes in PostgreSQL, expose it through a clean FastAPI layer, and keep a scheduler quietly refreshing the pipeline in the background so the dashboard always has something current to show.

You sit at the center of the pipeline — everyone feeds into you, and you feed everyone downstream:

```
Member 1 (Mann) — Collector
        ↓  FareObservation
Member 2 (Smit) — Index / Data Engine
        ↓  Index Values + Clean Data
[ YOU — DATABASE + REST API ]
        ↓  REST API + PostgreSQL
Member 4 — Analytics Engine (Lead-Time, Anomaly, Contribution)
        ↓
Member 5 — Government Dashboard
        ↓
FINAL DEMO
```

**The rule that protects the whole team:** *the frontend should retrieve data through APIs rather than directly accessing the database.* If Member 5 ever queries Postgres directly to save time, that's a shortcut that will break on demo day. Hold this line.

---

## 2. The Contracts You Sit Between

### 2.1 What you receive from Mann (raw) / Smit (computed)

Normalized fare observation (same shape the whole team agreed on in Hour 0–2):

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

Computed index value from Smit:

```json
{
  "date": "2026-09-10",
  "route": "DEL-BOM",
  "booking_window": "T+7",
  "index_value": 117.4
}
```

**Confirm with Smit** how the national aggregate is represented (e.g. `route: "NATIONAL"`) — pin this down in the freeze meeting so you don't have to renegotiate it at Hour 10.

**Confirm with Member 4** how anomaly/contribution results get written into your database — either they write directly using models you expose, or you give them a small internal write function. The blueprint doesn't spell this out; decide it explicitly rather than discovering the gap at integration time.

### 2.2 What you store — Database Schema (PostgreSQL)

| Table | Suggested Fields |
|---|---|
| `routes` | `id` (PK), `origin`, `destination`, `weight`, `active` |
| `carriers` | `id` (PK), `name`, `code` |
| `observations` | `id` (PK), `source`, `data_status`, `origin`, `destination`, `carrier`, `flight`, `travel_date`, `observed_at`, `booking_window`, `fare_class`, `base_fare`, `taxes`, `fees`, `total_fare`, `availability` |
| `index_values` | `id` (PK), `date`, `route`, `booking_window`, `index_value` |
| `anomalies` | `id` (PK), `observation_id` (FK → `observations.id`), `severity`, `score`, `detected_at`, `reason` |

(Field *types* — e.g. `numeric` for fares, `date`/`timestamp` for dates, `boolean` for `active` — aren't dictated by the blueprint; use sensible SQL types and confirm with the team once, then freeze them.)

### 2.3 What you expose — Minimum API Surface

| Endpoint | Purpose | Consumer |
|---|---|---|
| `GET /api/fares` | filterable by `route`, `carrier`, `date`, `booking_window`, `source` | M5, debugging |
| `GET /api/index/current` | latest national + route indices | M5 |
| `GET /api/index/history` | historical trend | M5 |
| `GET /api/routes` | list of tracked routes | M5 |
| `GET /api/routes/{route}` | detail for one route | M5 |
| `GET /api/lead-time` | fare-by-booking-window curve | M4 → M5 |
| `GET /api/anomalies` | flagged unusual movements | M4 → M5 |
| `GET /api/contributors` | "why did the index change" breakdown | M4 → M5 |
| `GET /api/validation` | AirIndex vs DGCA reference metrics | M4 → M5 |

---

## 3. What You're Building — 6 Tasks

### Task 1 — Database
PostgreSQL, with the five tables above created and related correctly (at minimum, `anomalies.observation_id` as a real foreign key).

### Task 2 — Observation API
`GET /api/fares` with filters on route, carrier, date, booking_window, and source — this is what lets everyone (including you, while debugging) inspect what's actually in the system.

### Task 3 — Index APIs
`GET /api/index/current`, `GET /api/index/history`, `GET /api/routes`, `GET /api/routes/{route}` — read Smit's `index_values` table and serve it cleanly.

### Task 4 — Analytics APIs
`GET /api/lead-time`, `GET /api/anomalies`, `GET /api/contributors`, `GET /api/validation` — these expose whatever Member 4 computes. You own the *endpoint*; Member 4 owns the *computation logic*.

### Task 5 — Pipeline Integration
Write the glue functions that take Mann's connector output, push it through validation, insert it, trigger Smit's index recalculation, and make the result queryable. This is the task most likely to reveal integration bugs — budget real time for it, don't treat it as "just wiring."

### Task 6 — Scheduler
A simple recurring job: every N minutes, pull fresh observations → store them → recalculate the index. Use **APScheduler or cron** — nothing more elaborate. This is a hackathon MVP, not a production data platform.

```
Every N minutes
    ↓
Collector (Mann)
    ↓
Database (you)
    ↓
Recalculate Index (Smit, triggered by you)
```

---

## 4. Priority Matrix

| MUST HAVE | DO NOT ATTEMPT |
|---|---|
| PostgreSQL, correctly modeled | Microservices |
| FastAPI | Kubernetes |
| CRUD / read APIs | A Kafka cluster |
| Collector integration | Authentication |
| Index integration | Payment systems |

If a teammate suggests "let's containerize this properly" or "let's add login so it looks more real" — that's scope creep. A single FastAPI process talking to a single Postgres instance is not just acceptable, it's the correct answer for this MVP.

---

## 5. Your Hour-by-Hour Track

| Hours | What You Do | Deliverable |
|---|---|---|
| 0–2 | **All-team freeze:** lock the DB schema, the API contracts, routes, booking windows, index methodology, git repo, and tech stack with the whole team. | Signed-off schema + API contract |
| 2–6 | Database + FastAPI skeleton | Tables created; app boots and responds on all planned endpoint paths (even with stub data) |
| 6–10 | Connect Mann's collector output into the database | `ingest_observations()` working against real (synthetic) data |
| 10 | **First integration checkpoint** — Collector → Database → Index → API → Dashboard must work end-to-end. If it doesn't, stop everything else and fix this join first. | A real request/response flowing through the whole pipeline once |
| 10–14 | API stability: filters actually work, error responses are clean, no crashes on empty/missing data | Robust API layer |
| 14–18 | Expose `/api/contributors` and `/api/anomalies` for Member 4's "why did the index change?" and anomaly-detection features | Endpoints ready and returning M4's data |
| 18–22 | Expose `/api/validation`; support documentation of the overall architecture in `docs/architecture.md` | Validation endpoint live; architecture doc drafted |
| 22–26 | Polish: consistent error handling, loading-friendly response shapes, CORS configured for Member 5's frontend, source-transparency fields (`source`, `data_status`) present in every relevant response | Demo-hardened API |
| 26–28 | **Feature freeze.** Run the scheduler + full pipeline repeatedly under the same conditions as the demo. | Verified stable, repeatable demo run |
| 28–30 | Jury prep — be ready to walk the judges through the architecture end-to-end. | Talking points ready |

---

## 6. Deliverable File Structure

```
backend/
├── main.py
├── models/
├── routes/
├── services/
└── database/
```

Working API + DB is the deliverable — not a diagram of one.

---

## 7. Definition of Done

> "All modules can communicate through a stable database/API."

Checklist:
- [ ] All five tables exist with correct relationships (esp. `anomalies.observation_id` FK)
- [ ] Every endpoint in Section 2.3 responds with real data, not just a stub
- [ ] `GET /api/fares` filters work correctly in combination (route + carrier + date, etc.)
- [ ] Unknown route/date returns a clean 404 or empty result — never a raw 500
- [ ] `source` and `data_status` are visible in every API response that includes fare data
- [ ] Scheduler runs on its own, end-to-end, without manual triggering
- [ ] Scheduler can't double-run concurrently
- [ ] Frontend (Member 5) never needs direct DB access to get anything it needs
- [ ] CORS is configured so the frontend can actually call the API from the browser

---

## 8. Using AI Tools to Move Fast

Paste the schema (Section 2.2) and the endpoint list (Section 2.3) into every prompt so generated code matches what the rest of the team is expecting. Backend boilerplate (models, CRUD routes, migrations) is exactly the kind of work AI tools are fast and reliable at — spend your own attention on the integration points (Task 5) where the real risk is.

### Prompt templates you can copy-paste

**(a) Database models + migration**
```
Using SQLAlchemy for PostgreSQL, generate models for these tables:
routes(id, origin, destination, weight, active),
carriers(id, name, code),
observations(id, source, data_status, origin, destination, carrier, flight,
  travel_date, observed_at, booking_window, fare_class, base_fare, taxes, fees,
  total_fare, availability),
index_values(id, date, route, booking_window, index_value),
anomalies(id, observation_id [FK -> observations.id], severity, score,
  detected_at, reason).
Use sensible types (numeric for money fields, date/timestamp appropriately).
Also generate an Alembic migration that creates these tables.
```

**(b) FastAPI skeleton + read endpoints**
```
Build a FastAPI app with SQLAlchemy dependency-injected sessions and these
read-only endpoints against the models above:
GET /api/fares (filterable by route, carrier, date, booking_window, source)
GET /api/index/current
GET /api/index/history
GET /api/routes
GET /api/routes/{route}
Each should return clean JSON. Return a 404 with a clear JSON error message
(never a raw 500) when a route or date has no matching data. Add CORS
middleware allowing requests from a local frontend dev server.
```

**(c) Pipeline integration functions**
```
Write two Python functions for a FastAPI + SQLAlchemy backend:
ingest_observations(observations: list[dict]) — validates each dict against
the observations table schema, skips exact duplicates (same source, route,
carrier, travel_date, booking_window, fare_class, observed_at), and bulk-inserts
the rest. Log how many were inserted vs skipped.
recompute_index() — pulls the latest observations from the database, calls
index-engine functions (I'll provide the function signatures) to compute route
and national index values, and upserts the results into index_values.
```

**(d) Scheduler**
```
Using APScheduler, add a background job to my FastAPI app that runs every N
minutes and, in order, calls: (1) a collector function to fetch new
observations, (2) ingest_observations(), (3) recompute_index(). Prevent the
job from running twice concurrently, and make sure any exception inside the
job is logged and does not crash the FastAPI application.
```

**(e) Error-handling tests**
```
Write pytest tests for my FastAPI app (using TestClient) that check:
GET /api/routes/{route} returns 404 with a JSON body for an unknown route;
GET /api/index/current still returns 200 with an empty/default structure when
there's no data yet; GET /api/fares with filters matching nothing returns an
empty list, not an error.
```

---

## 9. Common Pitfalls

- **Over-building the infrastructure** — microservices, Kubernetes, a Kafka cluster, or auth are explicitly out of scope. A single FastAPI app + single Postgres instance is the *correct* architecture here, not a compromise.
- **Letting the frontend query the database directly "just to save time"** — this breaks the API-first contract everyone else is relying on and tends to surface as a demo-day surprise.
- **Returning 500s for normal "no data yet" situations** — e.g. a route that hasn't been scraped yet should return an empty result or a clean 404, not a crash.
- **Dropping `source`/`data_status` from API responses** — these fields are the backbone of the project's "transparent, auditable" pitch (Member 5's data-provenance screen depends on them being present).
- **Scheduler races** — the recompute job overlapping with an in-flight API read, or running twice at once. Guard against concurrent runs even in a simple way.
- **Forgetting CORS** — a working API that the frontend's browser can't actually call is invisible progress from a demo perspective.
- **Treating Task 5 (integration) as trivial wiring** — it's usually where hidden bugs live; give it real time, not leftover time.

---

## 10. Jury Q&A You Should Be Ready For

**Q: Walk us through what happens from data collection to the dashboard.**
> A collector produces standardized fare observations, which are normalized and matched into comparable groups, converted into price relatives and a Jevons-based index, stored in PostgreSQL, and served through a FastAPI layer that the dashboard queries — refreshed on a scheduled interval rather than requiring manual updates.

**Q: Why FastAPI and PostgreSQL instead of a more "modern" distributed stack?**
> The data is naturally relational — routes, carriers, observations, and index values — and the project's constraint is a 24–30 hour build window, not production scale. A single well-structured API and database is more reliable to demo and defend than infrastructure that adds risk without adding value at this stage.

---

## 11. Quick Reference

- **Your one-line done-condition:** *"All modules can communicate through a stable database/API."*
- **Your non-negotiables:** frontend talks to your API only, never the DB directly; every fare-related response carries `source`/`data_status`; no 500s for ordinary missing-data cases.
- **Your safety net:** if time runs short, a simpler API that reliably returns correct data beats a feature-complete one that occasionally crashes mid-demo.
