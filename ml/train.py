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
    SELECT city, permit_type, cost, issued_date, wait_days
    FROM clean_permits
"""

connection = psycopg.connect(database_url)
rows = connection.execute(query).fetchall()
connection.close()

# turn the rows into a pandas table
columns = ["city", "permit_type", "cost", "issued_date", "wait_days"]
permits = pd.DataFrame(rows, columns=columns)
permits["issued_date"] = pd.to_datetime(permits["issued_date"])

# the model needs cost as a plain number, and city and type marked as categories
permits["cost"] = permits["cost"].astype(float)
permits["city"] = permits["city"].astype("category")
permits["permit_type"] = permits["permit_type"].astype("category")

# same split as the baseline, so the scores compare fairly
cutoff = pd.Timestamp("2026-08-01")
train = permits[permits["issued_date"] < cutoff]
test = permits[permits["issued_date"] >= cutoff]

# the columns the model learns from, all known on the day someone applies
features = ["city", "permit_type", "cost"]

# train one model per percentile, then grade each on the newer permits
for percentile in [0.5, 0.8, 0.9]:
    model = HistGradientBoostingRegressor(loss="quantile", quantile=percentile, random_state=0)
    model.fit(train[features], train["wait_days"])
    predictions = model.predict(test[features])

    # share of real waits that came in at or under the guess
    covered = (test["wait_days"] <= predictions).mean()

    print(percentile)
    print(covered)
    print(pinball_loss(test["wait_days"], predictions, percentile))

