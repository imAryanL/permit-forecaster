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

**2026-11-01: Score the baseline at the 50th, 80th and 90th percentiles with coverage and pinball loss.**
Why: the app shows a typical wait and a slow-case wait, and average error only scores the typical one. Coverage alone can be cheated: forecasting 1,460 days for every permit covers 100% and tells nobody anything. Pinball loss gives that forecast a bad score, so it shows whether a forecast is tight as well as reliable.
| Percentile | Coverage | Pinball loss |
|---|---|---|
| 50th | 51.5% | 31.99 |
| 80th | 79.5% | 37.02 |
| 90th | 89.7% | 30.21 |

Coverage by city:
| City | 50th | 80th | 90th |
|---|---|---|---|
| Austin | 52.4% | 80.1% | 91.7% |
| Chicago | 51.8% | 79.1% | 88.3% |
| Miami | 49.7% | 80.1% | 89.2% |
| Orlando | 54.0% | 80.8% | 89.0% |
| San Francisco | 47.3% | 75.1% | 87.5% |

What it means: coverage is already on target, so the model has to win on pinball loss by giving tighter forecasts with the same coverage. San Francisco runs a little low at every percentile, which is worth watching in the model.
I wrote the pinball function by hand and checked it: at the 50th percentile it comes out to exactly half the average error (31.99 × 2 = 63.97).
Known limit: pinball scores only compare at the same percentile. The 90th scoring lower than the 80th doesn't make it better.

## Model

**2026-11-06: Tried applied month (1 to 12) as a clue. Dropped it.**
What I found: overall pinball got worse at all 3 percentiles, 31.11 / 36.55 / 29.13 with the month vs 30.56 / 35.10 / 28.54 without it (50th / 80th / 90th). Every city was worse or tied. The biggest drop was Austin at the 80th, 54.30 vs 51.33. Coverage stayed on target (50.4%, 80.4%, 90.8%).
Why: a clue stays only if the overall score improves and no city gets clearly worse. My guess is that with about 3 years of data, each month shows up only 3 times, so the model learned month patterns that didn't hold for the newer permits.
Only the month, never the year: the split is on issued date, so the year would teach the model that newer permits are faster, which is a leak.

**2026-11-06: Tried applied weekday (Monday to Sunday) as a clue. Dropped it.**
What I found: a tie that leans slightly worse. Overall pinball was 30.58 / 35.22 / 28.61 with the weekday vs 30.56 / 35.10 / 28.54 without it. Every city moved by less than 1%, either way. Coverage stayed on target (50.3%, 81.1%, 91.0%).
Why: it doesn't improve the overall score, so it doesn't earn a place. That's two calendar clues in a row that didn't help, so I'm done with calendar clues.

**2026-11-06: Tried city busyness as a clue. Dropped it.**
How I measured it: the number of permits the city issued in the 30 days before this permit was applied for. Not the number filed, because my data only has permits that were issued, so a "filed" count would be missing everything still waiting and would depend on the future. Permits applied before 2023-01-31 got a blank, because their 30 days start before my data does (8.5% of rows).
What I found: pinball got a little better overall, 30.50 / 34.64 / 28.47 vs 30.56 / 35.10 / 28.54, but coverage fell well below target: 45.2%, 74.9% and 86.4% instead of about 50%, 80% and 90%. So the forecasts came out too low, and the slow-case number would be wrong more often than it promises. SF and Austin got better (SF 80th 19.76 vs 21.04), but Miami was worse at all 3 percentiles, Orlando worse at the 80th and 90th (12.22 vs 11.92), and Chicago worse at the 90th (10.30 vs 9.94).
Why: it breaks the keep rule (cities got worse) and it breaks coverage. My guess is that busyness changes over time, so the model used it as a stand-in for "how recent," and recent permits in the training data look fast only because the slow ones weren't issued yet. That's the same newer-means-faster trap as applied year, through a back door.
Lesson: check coverage, not only pinball. A better pinball with broken coverage is not a better forecast.
That's three clues in a row that didn't help (month, weekday, busyness). The model stays at city, permit type and cost.

**2026-11-06: Tried work category as a clue. KEPT it.**
What it is: the kind of work, picked on the application. Chicago: review track (express, standard plan review, self cert). Austin and Orlando: kind of work (new, repair, remodel, roof). Miami: commercial or residential. San Francisco: the building's existing use. It's filled in for 99.7% of permits. Same cleaning as permit types: any category with fewer than 50 permits in its city becomes OTHER, which leaves 100 categories.
What I found: the biggest gain yet, and coverage stayed on target (49.8%, 80.2%, 90.9%).
| Percentile | Without | With work category | Better by |
|---|---|---|---|
| 50th | 30.56 | 27.52 | 10% |
| 80th | 35.10 | 29.95 | 15% |
| 90th | 28.54 | 23.89 | 16% |
Against the baseline (31.99 / 37.02 / 30.21) the model is now 14%, 19% and 21% better.
By city: Austin got much better (42.15 to 34.54 at the 50th, 42.59 to 30.69 at the 90th, up to 28% better). Orlando got 8 to 10% better and Chicago 6 to 7% better. Miami and San Francisco tied (every change under 2%).
Why it works: unlike the calendar clues, it describes the permit itself, how big the job is and which review lane it goes through. Austin gains the most because only 10% of Austin permits have a cost, so before this the model knew almost nothing about the size of an Austin job.
The model is now city, permit type, work category and cost.

**2026-11-06: Tried description word count as a clue. KEPT it.**
What it is: the number of words in the job description. Orlando has no descriptions, and empty ones count as blank, not 0.
What I found: better at all 3 percentiles, with coverage on target (49.3%, 80.5%, 90.9%).
| Percentile | Without | With word count | Better by |
|---|---|---|---|
| 50th | 27.52 | 26.68 | 3% |
| 80th | 29.95 | 28.79 | 4% |
| 90th | 23.89 | 22.86 | 4% |
Against the baseline (31.99 / 37.02 / 30.21) the model is now 17%, 22% and 24% better.
By city: Miami is the big gain (51.46 to 47.41 at the 50th, 40.80 to 36.41 at the 90th, 8 to 11% better). Chicago and Austin got 1 to 2% better. Orlando and San Francisco tied (Orlando has no descriptions, so a tie is expected there).
Leak check: Miami's description is its scope of work, picked from a list on the application ("FLAT ROOF", "WINDOWS / DOORS / SKYLIGHT", sometimes several joined with |). More words means more pieces of work, and the median wait climbs from about 40 days at 1 to 4 words to about 300 days at 20+. It's known on the day someone applies, so it isn't a leak.
What it hints at: the words themselves matter, not only how many there are. In Miami, "REPLACE SAME LOCATION CENTRAL AC / HEATING SYSTEM" has a median wait of 0 days and "SEWER CAPPING" has 218. That's the case for the LLM description categories.
The model is now city, permit type, work category, cost and description word count.

**2026-11-06: Tried common descriptions as a clue. KEPT it, for now.**
What it is: each city's 60 most common exact descriptions (trimmed, uppercased) become categories, and everything else is OTHER. That makes 240 categories, under the model's 255 limit.
How much it covers: exact repeats are rare outside Miami because people write the same job many ways ("REROOFING", "RE-ROOFING", "REROOF"). The top 60 cover 58% of Miami permits, 17% of Austin, 13% of San Francisco and 6% of Chicago. Orlando has no descriptions.
What I found: better at all 3 percentiles, with coverage on target (49.7%, 79.7%, 90.9%).
| Percentile | Without | With common descriptions | Better by |
|---|---|---|---|
| 50th | 26.68 | 26.16 | 2% |
| 80th | 28.79 | 27.90 | 3% |
| 90th | 22.86 | 22.02 | 4% |
Against the baseline (31.99 / 37.02 / 30.21) the model is now 18%, 25% and 27% better.
By city: Miami again (47.41 to 45.15 at the 50th, 36.41 to 32.63 at the 90th, 5 to 10% better). Chicago and Austin about 1% better. San Francisco and Orlando tied.
Why "for now": it's a crude version of the LLM step. It only helps where descriptions repeat word for word. The LLM categories should replace it, and they have to beat 26.16 / 27.90 / 22.02 to earn their place.
Ties at 60th place in Chicago and San Francisco are broken by the order pandas sorts them in, which moved 116 permits and the scores by less than 0.05.
The model is now city, permit type, work category, cost, description word count and common description.

**2026-11-06: Checked tonight's kept clues on a practice test they were never picked on.**
Why: I graded 7 versions against the same Aug-Oct test permits tonight. Keeping whatever scores best on one test can tune the model to those exact permits, like checking the answer key after every question. So I made a practice test: train on permits issued before 2026-05-01 (572,422) and grade on May-July 2026 (43,596), then compared the old 3 clues (city, permit type, cost) with the new 6.
| Percentile | 3 clues | 6 clues | Better by (practice) | Better by (real test) |
|---|---|---|---|---|
| 50th | 31.22 | 26.61 | 15% | 14% |
| 80th | 36.18 | 28.73 | 21% | 21% |
| 90th | 29.24 | 22.69 | 22% | 23% |
Every city improved on the practice test too: Austin 20 to 29%, Miami 11 to 18%, Chicago and Orlando 8 to 12%, San Francisco 1 to 4%. Coverage stayed on target (52.0%, 81.1%, 91.3%).
What it means: the gains hold up on months the decisions never saw, almost to the percent, so they're real and not luck on the test set.
From now on: new ideas get picked on the practice test, and the real test is only for the final check.
