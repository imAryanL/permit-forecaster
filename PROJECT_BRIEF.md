# Project brief: permit wait-time forecaster

Written 2026-10-10. This brief is for Aryan and for any Claude Code session helping with the build. It is self-contained: a new session should read all of it before doing anything.

## 1. What this is

A full-stack web app that predicts how long a city will take to approve a building permit, using the city's own public permit records.

A user picks a city, a type of work and its cost. The app answers something like: "Permits like this typically take 21 days. One in ten takes longer than 60."

Likely users are contractors, permit expediters and homeowners planning a project.

## 2. Why Aryan is building it

Aryan is a December 2025 computer-science graduate (FAU, AI minor) looking for entry-level software, full-stack and AI engineering roles. This is a portfolio and learning project. Revenue is not a goal.

**What Aryan already has:** a native iOS app with 2,000+ downloads, a Next.js and Supabase SaaS with Stripe payments, a React Native app, and a freelance Next.js site. Aryan is comfortable in TypeScript, React and Next.js.

**What the portfolio is missing, and this project must add:**
- A backend in Python, written by hand.
- A database designed and queried with hand-written SQL.
- A trained machine-learning model, measured against a baseline. Aryan trained models in coursework but has never put one in a project.
- An LLM step whose output is checked and measured, not one unmeasured API call.
- Automated tests, automated checks on every commit, and Docker. None of Aryan's current repositories have any of these.

**Why those gaps matter:** in a sample of 32 entry-level postings from October 2026, Python appeared in 15, automated testing in 12 and SQL in 9. Five of 11 AI-engineer postings asked for evaluation experience.

**Why this idea:** a search found no existing product that forecasts permit wait times, the data is public, and the topic is new for Aryan (earlier projects covered school, weather and bookmarks).

## 3. Working rules for the Claude session

These matter more than anything else in this brief.

1. **Aryan writes the Python and the SQL.** Claude explains concepts, suggests an approach, reviews what Aryan wrote, and points out bugs. Claude does not write the Python or SQL logic. On two earlier take-home projects an agent wrote the code, and Aryan could not explain it afterwards. The purpose of this project is to fix that.
2. **Claude may write** configuration and scaffolding that teaches nothing: `.gitignore`, the CI workflow file, a Dockerfile skeleton. Explain each line when asked.

   **Split agreed 2026-10-11 (this refines rules 1 and 2).** Both write code. Aryan writes the core: the SQL migrations and the wait-days queries, the Orlando ingest script, the inputs, the baseline, training and evaluation, the LLM labeling call and agreement score, and the `/forecast` function. Claude writes: config, CI and Docker files, test setup and boilerplate, the Next.js page, the FastAPI wiring around Aryan's functions, and the second and third city's ingest once Aryan has written the first. Claude walks Aryan through anything Claude wrote.

   **Update 2026-10-18:** the split is a default, not a hard rule. Aryan decides case by case and can ask Claude to write a piece of the core (for example, Claude wrote the small `ingest_runs` table). Claude still explains anything it writes.
3. **Aryan already knows Next.js,** so normal help on the front end is fine.
4. **Keep everything simple enough to explain in an interview.** Prefer plain functions over clever abstractions. No framework that Aryan cannot describe in two sentences.
5. **Check understanding as you go.** After each piece, ask Aryan to explain it back. If Aryan can't, slow down.
6. **Python and SQL are rusty.** Assume coursework-level knowledge. Teach as you go; week 1 is partly relearning.
7. **No secrets in the repository, ever.** `.env` goes in `.gitignore` in the first commit. Aryan has had a leaked API key before.
8. **Do not suggest switching to a different project idea** unless a test in section 9 fails.

## 4. Data sources

**Five cities, decided 2026-10-17:** two in Florida (Orlando, Miami) and three well-known US cities (Chicago, San Francisco, Austin). All five were ingested by 2026-10-27 (664,069 permits since 2023), so version 1 can use all five.

All five were queried live on 2026-10-17 with no login.

| City | System | Records | Latest permit (as of 10/17) | Description text | Endpoint |
|---|---|---|---|---|---|
| Orlando | Socrata | Of permits issued since 2023, 120,060 have both `processed_date` and `issue_permit_date`. | **2026-09-23** (about 3.5 weeks behind, though the dataset says it updates daily) | None. `project_name` is a project or subdivision name, not a description. | `https://data.cityoforlando.net/resource/ryhf-m453.json` |
| City of Miami | ArcGIS | 235,060 records since 2014. All issued ones have `PlanCreatedDate` and `IssuedDate`. `FirstSubmissionDate` is mostly empty. | 2026-10-16 | `WorkItems`, short labels such as "WINDOWS / DOORS / SKYLIGHT", plus `ScopeofWork` | `https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer/0` |
| Chicago | Socrata | Of permits issued since 2024, 91,195 have both `application_start_date` and `issue_date`. 58,490 of them are "Express Permit Program". | 2026-10-16 | `work_description`, real free text | `https://data.cityofchicago.org/resource/ydr8-5enu.json` |
| San Francisco | Socrata | Of permits issued since 2024, 65,744 of 66,196 have both `filed_date` and `issued_date` (checked 10/10). Dates include a time of day. | 2026-10-16 | `description`, real free text | `https://data.sf.gov/resource/i98e-djp9.json` (the old `data.sfgov.org` domain redirects here) |
| Austin | Socrata | Of permits issued since 2024, 154,640 of 154,640 have both `applieddate` and `issue_date` (checked 10/10). | 2026-10-16 | `description`, real free text | `https://data.austintexas.gov/resource/3syk-w9eu.json` |

**Each city publishes its own wait figure:** Orlando `day_to_issuance`, Miami `DaysInCity` and `TotalDaysInPlanReview`, Chicago `processing_time`. Compute wait days from the two dates, then compare with these as a sanity check.

**Orlando's lag is gone.** It was about 3.5 weeks behind on 10/17, but the data was current to 10/21 when loaded on 2026-10-21.

**Florida search, 2026-10-17:** the Socrata catalog and an ArcGIS search found no other Florida city with both an application date and an issue date in an open API. Gainesville's dataset stopped in 2023; Tallahassee and Leon County publish active permits only; Fort Lauderdale has no record with both dates; Miami-Dade County has the application date only; Broward has nothing. Orlando and Miami are the only two Florida options.

**Other large cities with both dates (checked 2026-10-10, not planned)**

| City | Socrata dataset | Application and issue fields | Permits issued since 2024 with both |
|---|---|---|---|
| New Orleans | `data.nola.gov` `rcm3-fn58` | `filingdate`, `issuedate` | 49,816 of 49,824 |
| Seattle | `data.seattle.gov` `76t5-zqzr` | `applieddate`, `issueddate` | 16,158 of 17,243 |
| New York City | `data.cityofnewyork.us` `ipu4-2q9a` | `filing_date`, `issuance_date` (stored as text, `MM/DD/YYYY`) | 3,969,934 in total. No description field, and New York moved to a newer permit system, so this dataset may be partial. Skip. |

Not usable as they stand: Los Angeles (`pi9x-tg5x` has an issue date only; a separate "submitted" dataset, `gwh9-jnip`, might be joined to it but was not checked) and Dallas (issue date only).

**Fields seen**
- **Orlando:** `permit_number`, `application_type`, `worktype`, `plan_review_type`, `estimated_cost`, `square_footage`, `processed_date`, `prescreen_completed_date`, `pending_issuance_date`, `issue_permit_date`, `final_date`, `application_status`, `of_cycles`, `private_provider`, `project_name`, `neighborhood`.
- **Miami:** `FirstSubmissionDate`, `PlanCreatedDate`, `PlanAcceptedDate`, `IssuedDate`, `Statusdate`, `ScopeofWork`, `WorkItems`, `TotalCost`, `NewAdditionCost`, `RemodelingCost`, `PropertyType`, `BuildingPermitStatusDescription`.
- **Chicago:** `permit_type`, `review_type`, `work_type`, `work_description`, `application_start_date`, `issue_date`, `processing_time`, `reported_cost`, `total_fee`.
- **San Francisco:** `permit_type_definition`, `description`, `estimated_cost`, `filed_date`, `issued_date`.
- **Austin:** `permittype`, `work_class`, `description`, `applieddate`, `issue_date`.

**How to query**
- **Socrata:** add `$limit`, `$offset`, `$order` and `$where` to the URL. Page through in chunks; large unfiltered queries time out.
- **ArcGIS:** call `/query?where=1=1&outFields=*&resultOffset=0&resultRecordCount=1000&f=json`. Dates come back as milliseconds since 1970. Read `maxRecordCount` from the layer's metadata (`?f=pjson`) for the page size.

**Not usable:** Miami-Dade County (application date only), Fort Lauderdale (no record has both dates), Broward County (no dataset found). There is no free national source.

**Privacy:** the datasets include owner names, contractor names and phone numbers. Do not store or display them. Keep only the columns the model needs.

## 5. Architecture

```
City data portals (Orlando, Miami, Chicago; later San Francisco, Austin)
        |  ingest job, one module per city (scheduled nightly)
        v
   Postgres  <---- LLM labeling step (work description -> category)
        |
        |  training script (inputs, model, evaluation report)
        v
   Saved model file + metrics
        |
   FastAPI service  (/forecast, /stats, /cities)
        |
   Next.js page  (pick city, type, cost -> see the forecast)
```

Train locally against the full data. The hosted app only needs the model file and small summary tables, which keeps it inside free database limits.

## 6. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3 |
| API | FastAPI with Pydantic |
| Database | Postgres; plain numbered `.sql` migration files; no ORM |
| Data work | pandas |
| Forecast model | scikit-learn `HistGradientBoostingRegressor` with `loss="quantile"` |
| LLM step | A small, low-cost Claude model with schema-checked output (confirm current model names and prices when building) |
| Text classifier | TF-IDF plus logistic regression in scikit-learn |
| Tests | pytest |
| Automated checks | GitHub Actions |
| Packaging | Docker |
| Front end | Next.js, one page, on Vercel |
| API hosting | Render or similar; confirm current free tiers |

**Suggested repository layout**

```
permit-forecaster/
  PROJECT_BRIEF.md
  README.md
  ingest/            one module per city
  sql/migrations/    001_init.sql, 002_..., in order
  ml/                inputs, train, evaluate
  labeling/          LLM step and label files
  api/               FastAPI app
  web/               Next.js page
  tests/
  Dockerfile
  .github/workflows/ci.yml
```

**Database tables (sketch)**
- `permits`: city, permit number, permit type, work category, description, cost, applied date, issued date, wait days, status.
- `ingest_runs`: city, start time, rows added, success or failure.
- `label_samples`: permit id, Aryan's label, the LLM's label.
- `model_runs`: trained date, training cutoff, metrics.

**API endpoints (sketch)**
- `GET /cities` and `GET /permit-types?city=`
- `POST /forecast`: city, type, cost, optional description. Returns the typical wait, the slow-case wait, and how many similar permits the answer rests on.
- `GET /stats?city=&type=` for a history chart.
- `GET /health`

## 7. The machine learning

- **Target:** days from application to approval.
- **Output:** the 50th, 80th and 90th percentile wait.
- **Inputs:** city, permit type, work category, cost, month, weekday, and how backed up the office is (applications and approvals in the previous 30 and 90 days).
- **Baseline to beat:** the median wait over the previous 90 days for the same city and permit type.
- **Test:** train on older months and test on the most recent months, which the model never saw.
- **Scores to report:** pinball loss (the standard error measure for percentile forecasts), how often the real wait falls under the 90th-percentile forecast, and average error in days.

**Known traps**
- **Leaking the answer.** Orlando's `of_cycles` (review rounds) is only known after approval. Never use it as an input. Check every input for this.
- **Open permits.** Records of issued permits leave out ones still waiting, which makes waits look shorter than they are.
- **Same-day permits.** Many simple permits are approved instantly. Consider treating them separately.
- **Date meanings differ by city.** Use `processed_date` as Orlando's application date; it matched `prescreen_completed_date` in every sampled row. Use `PlanCreatedDate` as Miami's, because `FirstSubmissionDate` is empty on about 83% of records. Whether `PlanCreatedDate` is the true filing date is not confirmed; read Miami's data dictionary in week 1. Use `application_start_date` for Chicago, `filed_date` for San Francisco and `applieddate` for Austin. San Francisco's dates include a time of day; round to the date.

## 8. The LLM step

1. Aryan hand-labels about 300 work descriptions into 10 to 15 categories.
2. The LLM labels the same 300. Measure how often it agrees with Aryan.
3. The LLM labels a few thousand more.
4. Train the small text classifier on those labels and apply it to the remaining records. This avoids paying for a million LLM calls.
5. Train the forecast model with and without the category, and report the difference.

Confirmed 2026-10-17: Chicago's `work_description`, San Francisco's `description` and Austin's `description` are real free text, so pull the 300 hand-label samples from those cities. Miami's `WorkItems` are short labels that may map to categories without an LLM. Orlando has no description field; it gets the category from `application_type` and `worktype` only.

## 9. Schedule and tests

About 8 weeks at roughly 15 hours a week. The week estimates are a judgment, not a measured figure.

The dates below assume a start on Thursday 2026-10-15. Work actually started Saturday 2026-10-17 (repository and first commit). If work starts earlier or later, shift every week by the same amount. "Aryan" and "Claude" follow the split in section 3.

| Week | Dates | Goal | Done when |
|---|---|---|---|
| 1 | Oct 15 to Oct 21 | Data in Postgres and a baseline score | Aryan knows which date fields to use and what the baseline scores. |
| 2 | Oct 22 to Oct 28 | First model, tested against the baseline | A table shows model against baseline. |
| 3 | Oct 29 to Nov 4 | **Version 1 live** | A stranger can get a forecast from a public link. |
| 4 | Nov 5 to Nov 11 | Scheduled ingest and a third city | The job has run unattended for five nights. |
| 5 | Nov 12 to Nov 18 | LLM labeling, measured | There is an agreement number. |
| 6 | Nov 19 to Nov 25 | Text classifier, San Francisco and Austin, final results | The results table is final, with five cities. |
| 7 | Nov 26 to Dec 2 | Reliability and write-up (Thanksgiving week, expect fewer hours) | Someone else can run it from the README. |
| 8 | Dec 3 to Dec 9 | Buffer and sharing | Unfinished items are cut, not carried over. |

### Week 1 (Oct 15 to Oct 21): data and baseline
- Claude: repository setup, `.gitignore` with `.env`, pytest setup, the GitHub Actions workflow.
- Aryan: get `psql` working and create the database.
- Aryan: write `sql/migrations/001_init.sql` for `permits` and `ingest_runs`.
- Aryan: write the Orlando ingest script (one page first, then paging and inserts).
- Claude: write the Miami ingest script after Aryan's Orlando one works, and walk Aryan through it.
- Aryan: write the SQL that computes wait days and counts records with both dates.
- Aryan: compute the baseline (median wait over the previous 90 days by city and permit type).
- Done 2026-10-30: compared date fields to confirm Miami's `PlanCreatedDate` and Orlando's `processed_date` (see `DECISIONS.md`).

### Week 2 (Oct 22 to Oct 28): first model
- Aryan: clean the data (bad dates, negative waits, same-day permits).
- Aryan: build the inputs, including the office-busyness counts.
- Aryan: write the time split (older months to train, newest months to test).
- Aryan: train the percentile forecast model and score it with pinball loss and coverage.
- Aryan: write the first tests for the cleaning and input functions.
- Check the week-2 test below. If it fails, switch to the fallback.

### Week 3 (Oct 29 to Nov 4): version 1 live
- Aryan: write the `/forecast` function that loads the model and returns the three numbers.
- Claude: FastAPI wiring around it, plus `/cities`, `/permit-types` and `/health`.
- Claude: the Next.js page (form, three numbers, history chart, trust panel), using the prototype as the visual reference.
- Claude: the Dockerfile. Aryan installs Docker Desktop and runs it.
- Deploy the API and the page. Put the link in the README.

### Week 4 (Nov 5 to Nov 11): scheduled ingest and Chicago
- Aryan: make the ingest scripts safe to re-run (no duplicate rows) and record each run in `ingest_runs`.
- Claude: the scheduled GitHub Action that runs ingest nightly.
- Claude: the Chicago ingest script. Aryan reviews it against the Orlando one.
- Aryan: retrain with three cities and update the results table.

### Week 5 (Nov 12 to Nov 18): LLM labeling
- Aryan: choose 10 to 15 work categories from real descriptions.
- Aryan: hand-label about 300 descriptions.
- Aryan: write the LLM labeling call with schema-checked output.
- Aryan: run Haiku 5.5 and Sonnet 5.5 on the 300 and compute each one's agreement with the hand labels. Keep the cheaper model if they tie.
- Set a spending cap on the API account before running anything.

### Week 6 (Nov 19 to Nov 25): classifier and results
- Claude: the San Francisco and Austin ingest scripts, following Aryan's Orlando and Chicago ones. Aryan reviews them.
- Aryan: have the chosen LLM label a few thousand more descriptions (use the Batch API).
- Aryan: train the TF-IDF and logistic regression classifier on those labels and score it on the hand-labeled set.
- Aryan: retrain the forecast model on all five cities, with and without the category, and record the difference.
- Aryan: break the errors down by city and permit type, and write up where the model is weak.

### Week 7 (Nov 26 to Dec 2): reliability and write-up
- Claude: timeouts, retries and logging around the ingest and the API. Aryan reviews.
- Aryan: README with the architecture diagram, the results table and the known limits.
- Build the "How it works" page with the real "did the 9-in-10 estimate hold" chart.
- Record a short demo video.
- Read each data portal's terms of use before sharing the link widely.

### Week 8 (Dec 3 to Dec 9): buffer and sharing
- Finish anything that slipped, or cut it.
- Show the site to a few contractors or homeowners and note what they say.
- Write one post explaining how the model was built and measured.
- Add the project to the resume, with measured numbers only.
- If San Francisco or Austin slipped from week 6, finish them here or ship with three cities.

**Tests that decide whether to continue** (proposed thresholds, not published standards)
1. **End of week 1:** at least two cities have 20,000 or more records with both dates. This already passes for Orlando, Miami and Chicago (rechecked 2026-10-10), so week 1's real job is loading the data and scoring the baseline.
2. **End of week 2:** the model beats the baseline by about 10% on pinball loss in at least one city.

**If either fails:** switch to the fallback, a salary estimator for job postings that hide pay. Its data sources are already verified. Details are in `Desktop\reports\ML web app build guide.md` on the PC and in the email sent 2026-10-09.

**First session, in order**
1. Create the repository and the first commit: `.gitignore` (with `.env`), a README stub, an empty test that passes, the CI workflow.
2. Create the database. Postgres 17 is already installed on the PC (see section 13); get `psql` working first.
3. Write `sql/migrations/001_init.sql` for the `permits` and `ingest_runs` tables.
4. Write the Orlando ingest script: fetch one page, print it, then page through and insert.
5. Write one SQL query that computes wait days and counts how many records have both dates.

## 10. What "done" looks like

- A public link where anyone can get a forecast without signing up.
- A README with the architecture diagram, the results table, and an honest list of where the model is weak.
- Tests that run on every commit.
- Aryan can explain every Python file and every SQL query without notes.

**Resume bullets to fill in with measured numbers only**
- Built a permit wait-time forecaster in Python (FastAPI) and Postgres over [N] public permit records from [K] cities, with a nightly ingest job and hand-written SQL migrations.
- Trained a percentile forecast model that cut error [X]% against a recent-median baseline on [M] held-out months; the 90th-percentile forecast held [Y]% of the time.
- Used an LLM to categorize free-text work descriptions ([A]% agreement with [L] hand labels), then trained a text classifier on its labels; the categories improved the forecast by [Z]%. [T] tests run on every commit.

## 11. Out of scope

User accounts, payments, a mobile app, more than three cities before v1, more than five cities in total, Kubernetes, agent frameworks, vector databases. Add nothing from this list without a reason tied to section 2.

## 12. Not yet verified

- Terms of use for each data portal. Read them before launch.
- Whether anyone wants the tool. No demand evidence was found; Reddit could not be searched.
- Florida's 2026 permit laws (HB 927 and others) may fix some permit timelines by rule.
- Hosting free tiers. As of the research: Fly.io has no free tier for new accounts, Railway is a trial only, Neon's free Postgres holds 0.5 GB per project, and Supabase's free tier pauses after a week of inactivity.

Present every forecast as a statistic from past records, never as a guarantee or as legal advice.

## 13. Aryan's machine

The project is built on a Windows 11 PC, in PowerShell. The project folder is `C:\Users\aryan\Desktop\Projects\permit-forecaster`. Checked 2026-10-10:

| Tool | Status |
|---|---|
| Python | 3.12.5 installed (`python` and `py` both work) |
| Git | 2.46.0 installed |
| Node and npm | Node 24.11.1, npm 11.6.2 installed |
| Postgres | Version 17 installed and running as the Windows service `postgresql-x64-17`. `psql` is not on the PATH yet; add the Postgres `bin` folder to the PATH or call it by full path. |
| Docker | Not installed. Not needed until week 3; install Docker Desktop then. |
| GitHub CLI | Not installed. Optional; the GitHub website works for creating the repository. |

Use a Python virtual environment inside the project folder (`python -m venv .venv`) and keep `.venv` out of Git.
