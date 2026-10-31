# Decisions log

Every real choice in this project, in plain English, with the reason. Newest at the bottom of each section. If someone asks "why did you do it this way?", the answer should be here.

## The project

**2026-10-09: Build a permit wait-time forecaster.**
Why: I searched and found no existing tool that forecasts permit wait times, the data is public, and it fills the gaps in my portfolio (Python backend, hand-written SQL, a trained model measured against a baseline, a measured LLM step, tests and CI).

**2026-10-09: The goal is learning and a portfolio piece, not revenue.**
Why: it keeps the scope small enough to finish and explain.

## Data sources

**2026-10-17: Five cities: Orlando, Miami, Chicago, San Francisco, Austin.**
Why: I wanted two Florida cities, and Orlando and Miami are the only Florida cities with both an application date and an issue date in an open API. Miami-Dade County, Fort Lauderdale and Broward didn't have both. Chicago, SF and Austin are well-known cities with clean data and real free-text descriptions, which the LLM step needs.

**2026-10-27: No more cities. Five is final.**
Why: more cities means more ingest scripts to maintain and more to explain, but doesn't prove anything new. The time is better spent on the model.

**2026-10-17: Only permits issued since 2023-01-01.**
Why: recent permits reflect how each office works today. Older rules and staffing would make the forecast worse, not better. It also keeps the data a manageable size (664,069 rows).

**Which date counts as "applied" in each city:**
| City | Applied date | Issued date | Note |
|---|---|---|---|
| Orlando | `processed_date` | `issue_permit_date` | Matched `prescreen_completed_date` in every sampled row. |
| Miami | `PlanCreatedDate` | `IssuedDate` | `FirstSubmissionDate` is filled on only 3,390 of 116,635 rows, so it can't be used. Confirmed 2026-10-30 that `PlanCreatedDate` is the filing date (see Cleaning). |
| Chicago | `application_start_date` | `issue_date` | |
| San Francisco | `filed_date` | `issued_date` | Dates include a time of day; rounded to the date. |
| Austin | `applieddate` | `issue_date` | |

## Database

**2026-10-18: Plain Postgres with numbered `.sql` migration files, no ORM.**
Why: I want to show I can write SQL by hand, and an ORM would hide it.

**2026-10-18: One `permits` table for all five cities, with a `city` column.**
Why: every city maps into the same columns, so one table makes comparing cities a simple `GROUP BY city`.

**2026-10-18: `wait_days` is a generated column (`issued_date - applied_date`).**
Why: like an Excel formula column, Postgres computes it automatically, so it can never be out of sync with the dates.

**2026-10-18: `UNIQUE (city, permit_number)`.**
Why: two cities could use the same permit number, but the same city never should. This stops duplicate rows.

**2026-10-18: An `ingest_runs` table logs every ingest run.**
Why: when the nightly job runs on its own, I need a record of what ran, how many rows it added and whether it worked.

## Ingest

**2026-10-21: One ingest script per city in `ingest/`.**
Why: each city's API has different field names and quirks. Separate scripts keep each one simple to read.

**2026-10-21: Insert with `ON CONFLICT (city, permit_number) DO NOTHING`.**
Why: the scripts are safe to re-run. Permits I already saved are skipped instead of crashing or duplicating.

**2026-10-27: San Francisco keeps only rows with `primary_address_flag = 'Y'`.**
Why: SF lists one permit once per address, up to 8 times. Keeping the primary address gives one row per permit.

**2026-10-27: Austin has a 60-second timeout and retries 3 times.**
Why: Austin's server dropped the connection twice during the first full load.

**2026-10-27: Miami checks for an `"error"` key in each response.**
Why: ArcGIS sends errors back as a normal HTTP 200 response, so checking the status code alone misses them.

## Who does what

**2026-10-27: SQL cleans and stores, Python analyzes and predicts, FastAPI serves, Next.js shows.**
Why: each tool does the job it's best at, and it's easy to explain in one sentence.

**2026-10-27: I type the cleaning, baseline and model myself.**
Why: this is the part interviewers will ask about, and I need to be able to explain every line.

## Cleaning

**2026-10-30: Drop the 86 rows with a negative wait.**
What I found: Austin 41, Orlando 41, Chicago 2, San Francisco 2, Miami 0. The permit number has the real year in it (`BLD2023-20162`) and matches the issued date, so the applied date is the broken one. The city's system wrote a later date into it, likely when the permit was revised. Three unrelated Austin permits share the same applied date (2025-07-31), which looks like a bulk update.
Why drop: the real applied date is gone, so the true wait can't be recovered. Leaving them in would teach the model that permits can finish before they start. 86 rows is 0.01% of the data.
Known limit: if the system can overwrite the applied date with a later one, some normal-looking rows probably had it happen too. Those waits would look shorter than they really were, and there's no way to detect them. Goes in the README.

**2026-10-30: Cap waits at 4 years (1,460 days). Anything longer is dropped.**
What I found: I pulled random samples from three ranges.
| Wait | What it was |
|---|---|
| 2 to 4 years | Mostly real slow permits, like Miami new construction (permit number year matches the applied date). |
| 4 to 10 years | Mostly stalled or abandoned projects: a sign permit at 4.5 years, remodels at 4 to 6 years, a Revoked permit. The dates are real, but the wait measures the applicant going quiet, not the city reviewing. |
| 10+ years | Record-keeping junk: Austin permits applied for in the 1980s with issued dates in 2023 to 2026. |

Rows each cap would drop: over 2 years 16,456 (2.5%), over 3 years 7,681 (1.2%), over 4 years 4,010 (0.6%). Miami is where it matters: a 2-year cap would cut 5.3% of Miami, mostly real permits.
Why 4: it removes the stale rows the samples showed and keeps the slow but real ones. I considered 5 years, but the 4 to 5 year range in the sample was mostly stalled projects too.
Known limit: in Austin, trade permits (plumbing, mechanical, electrical) sometimes inherit the main project's applied date, so their wait can include time before the trade permit existed. Fixing it would mean decoding five permit number formats, so I left it and noted it.

**2026-10-30: Keep same-day permits (wait of 0 days) as normal rows.**
What I found: most come from a few types. SF "otc alterations permit" (42,681, OTC means over the counter), Chicago "EXPRESS PERMIT PROGRAM" (26,258) and "EASY PERMIT PROCESS" (6,914). These are real instant approvals, not bad data.
Why keep: in SF and Chicago the permit type already tells the model which permits are instant, so no special handling is needed. Simpler to explain.
Known limit: Orlando's same-day permits are spread across broad types (Building Permit 11,839, Electrical 10,961, Plumbing 8,621), so the type alone won't tell the model which Orlando permits are instant. Expect Orlando forecasts to be less sure.

**2026-10-30: Drop three permit types that aren't a normal permit wait.**
- Miami `BUILDING RECERTIFICATION/MILESTONE INSPECTION` (4,307): the safety inspection program for older buildings, not a construction permit.
- Chicago `PERMIT - REINSTATE REVOKED PMT` (1,378): bringing back an old permit, not a new application.
- Orlando `Concurrency Case` (62): a land-use review of whether roads and utilities can handle a project, not a building permit.
Why: nobody using the app would pick these to plan a project, and their waits measure a different process.

**2026-10-30: Keep Miami `SPECIAL EVENTS` (1,104).**
Why: it's a real permit (likely temporary tents and stages), just not a common pick. It's harmless to keep.

**2026-10-30: Group permit types with fewer than 50 permits into `OTHER` for that city.**
The 7 types: Miami `ANNUAL FACILITY` (25), `BOILER` (7), `LANDSCAPING` (7), `SHOP DRAWINGS - OTHER` (1), `COOKIE CUTTER` (1); Orlando `Low Voltage Stickers` (2); SF `grade or quarry or fill or excavate` (8). 51 rows total, 50 after the 4-year cap removes one Miami `LANDSCAPING` permit.
Why: too few examples to forecast each one alone, but I'd rather keep every permit in the system than drop them. The cutoff is 50, not 100, so SF `new construction` (65) keeps its own type.
Known limit: `OTHER` mixes unrelated permits, so its forecast is rough. The app should show how many permits each forecast is based on.

**2026-10-30: Treat a cost of $0 or less as missing (NULL). Keep the rows.**
What I found: usable cost (filled and above $0) is 99.6% of SF, 93% of Miami, 92% of Orlando, 89% of Chicago, but only 10% of Austin (21,859 of 217,192). Orlando is 100% filled, but 9,640 of those are $0, which means nobody entered it.
Why: no project costs $0, so a 0 means unknown. Left as 0, the model would think thousands of projects were free. Dropping rows without a cost would throw away 90% of Austin, and the model (`HistGradientBoostingRegressor`) handles missing inputs on its own.
Known limit: Austin forecasts mostly can't use cost, so they lean on permit type.

**2026-10-30: Keep every status. Never use status as a model input.**
What I found: status is what happened to the permit after it was issued (Final, Expired, Withdrawn, Revoked and so on). Every row has an issued date, so the city approved all of them. Austin Expired alone is 18,739 rows (8.6%).
Why keep: the wait is application to approval, and that happened normally no matter what the owner did later. The strange long-wait Withdrawn and Revoked rows are already removed by the 4-year cap.
Why not an input: a new applicant can't know if their permit will expire or be revoked. Using it would be leakage (the model gets a clue from the future it won't have in real life), the same trap as Orlando's `of_cycles`.

**2026-10-30: Keep `processed_date` as Orlando's applied date.**
What I found: Orlando's dataset has no field descriptions, so I compared the date fields on 15 recent Building Permits. `processed_date` was the earliest date in every row. `prescreen_completed_date` usually matched it, but sometimes came weeks later (`BLD2026-17307`: processed 8/27, prescreen 9/23). Permit numbers go up with `processed_date`, so the number is assigned when the application enters the system.
Why: it's the earliest date Orlando gives us, so it's the closest to when the applicant applied. The 2-day median is real: many simple Orlando permits are processed one day and issued the next.
Known limit: any time before the city logs the application is invisible. That's true for every city.

**2026-10-30: Keep `PlanCreatedDate` as Miami's applied date.**
What I found: Miami's field list has no descriptions, so I compared the dates on 20 permits from the city's API.
- On rows that have `FirstSubmissionDate`, `PlanCreatedDate` is the same day or 1 to 2 days earlier. So `PlanCreatedDate` is when the application was filed.
- The order is always `PlanCreatedDate` → `PlanAcceptedDate` → `IssuedDate`. Accepted is when the plans passed intake and review started. That gap can be months (`BD25019043001B001`: created 2025-08-05, accepted 2025-12-17).
- Miami's own `TotalDaysInPlanReviewNumeric` equals accepted to issued exactly (106 of 106, 315 of 315). Our wait is created to issued, so it's longer: it includes intake.
- `DaysInCityNumeric` is empty on recent permits, so it can't be used.
Why: the app answers "how long from applying to approval," which includes intake. Created to issued matches what we measure in the other cities.
Side check: the rows with a `FirstSubmissionDate` included 2012 permits issued in 2023 to 2025 (waits of 3,900 to 4,700 days). The 4-year cap removes them.

**2026-10-30: Replace the en dash in Chicago's `PERMIT – EXPRESS PERMIT PROGRAM` with a normal hyphen.**
What I found: it's the only Chicago type with an en dash (`–`). The other 8 use a hyphen (`-`).
Why: Postgres treats them as different text, so a query or the app typing a normal hyphen would match 0 rows. The model doesn't care, but it prevents a bug you can't see by looking.

**2026-10-30: All cleaning happens in a `clean_permits` view, not by deleting rows.**
Why: the raw `permits` table stays untouched, so any rule can be changed later by editing the view.

## Baseline

**2026-10-31: Split train and test on `issued_date`, not `applied_date`.**
What I found: the data only has issued permits, so slow permits applied for recently aren't in it yet. In Austin, the 90th percentile wait by applied month falls from 146 days (March 2026) to 12 days (October 2026). By issued month it stays steady, 314 and 291 days.
Why: splitting on applied date would fill the test months with only the fast permits and make every score look better than it really is.
Train is everything issued before 2026-08-01 (616,018 permits). Test is everything issued from 2026-08-01 through 2026-10-26 (38,556 permits).

**2026-10-31: The baseline is the median wait over the 90 days before the cutoff, by city and permit type.**
Why: it's the simple forecast the model has to beat. Without it, a model's score means nothing. It uses 42,926 permits issued from 2026-05-03 through 2026-07-31.
Score: off by 64.0 days on average. Austin 85.3, Chicago 24.3, Miami 115.5, Orlando 24.0, San Francisco 33.5.
Known limit: the medians are computed once at the cutoff, not updated through the test months. The model has to be tested the same way so the comparison is fair.
