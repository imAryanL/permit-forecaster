# Model: learns to forecast permit waits from older permits.
# It's tested on the same newer permits as baseline.py, and it has to
# beat the baseline's scores to be worth using.

import os

import pandas as pd
import psycopg
from dotenv import load_dotenv
from sklearn.ensemble import HistGradientBoostingRegressor

# read DATABASE_URL from the .env file
load_dotenv()
database_url = os.getenv("DATABASE_URL")

def pinball_loss(real, forecast, percentile):
    too_low = (real - forecast).clip(lower=0)
    too_high = (forecast - real).clip(lower=0)
    return (percentile * too_low + (1 - percentile) * too_high).mean()

query = """
    SELECT city, permit_type, work_category, description, cost, applied_date, issued_date, wait_days
    FROM clean_permits
"""

connection = psycopg.connect(database_url)
rows = connection.execute(query).fetchall()
connection.close()

# turn the rows into a pandas table
columns = ["city", "permit_type", "work_category", "description", "cost", "applied_date", "issued_date", "wait_days"]
permits = pd.DataFrame(rows, columns=columns)
permits["issued_date"] = pd.to_datetime(permits["issued_date"])
permits["applied_date"] = pd.to_datetime(permits["applied_date"])

# ---- clues, all known on the day someone applies ----

# work category: the kind of work picked on the application
# (Chicago: express or standard review, Miami: commercial or residential).
# Same rule as permit types: under 50 permits in a city becomes OTHER.
permits["work_category"] = permits["work_category"].str.strip().replace("", None)
category_size = permits.groupby(["city", "work_category"])["work_category"].transform("count")
permits.loc[category_size < 50, "work_category"] = "OTHER"

# description words: a longer description usually means a bigger job.
# Orlando has no descriptions, so those stay blank instead of 0.
permits["description_words"] = permits["description"].str.split().str.len()
permits.loc[permits["description_words"] == 0, "description_words"] = None

# common description: each city's 60 most common descriptions; the rest are OTHER
permits["common_description"] = permits["description"].str.strip().str.upper()
top_60 = permits.groupby("city")["common_description"].value_counts().groupby("city").head(60)
in_top_60 = permits.set_index(["city", "common_description"]).index.isin(top_60.index)
permits.loc[~in_top_60, "common_description"] = "OTHER"

# the model needs cost as a plain number, and the text clues marked as categories
permits["cost"] = permits["cost"].astype(float)
for column in ["city", "permit_type", "work_category", "common_description"]:
    permits[column] = permits[column].astype("category")

# same split as the baseline, so the scores compare fairly
cutoff = pd.Timestamp("2026-08-01")
train = permits[permits["issued_date"] < cutoff]
test = permits[permits["issued_date"] >= cutoff]

# the columns the model learns from, all known on the day someone applies
features = ["city", "permit_type", "work_category", "cost", "description_words", "common_description"]

# train one model per percentile, then grade each on the newer permits
for percentile in [0.5, 0.8, 0.9]:
    model = HistGradientBoostingRegressor(loss="quantile", quantile=percentile, random_state=0)
    model.fit(train[features], train["wait_days"])
    predictions = model.predict(test[features])

    # put each permit's guess next to its real wait
    scored = test.copy()
    scored["forecast"] = predictions

    # grade each city on its own
    for city in scored["city"].unique():
        one_city = scored[scored["city"] == city]
        print(city, pinball_loss(one_city["wait_days"], one_city["forecast"], percentile))

    # share of real waits that came in at or under the guess
    covered = (test["wait_days"] <= predictions).mean()

    print(percentile)
    print(covered)
    print(pinball_loss(test["wait_days"], predictions, percentile))

