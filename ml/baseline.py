# Baseline: the simple forecast the model has to beat.
# For each city and permit type, it predicts the 50th, 80th and 90th percentile
# wait from recent permits, then scores those against newer permits it never saw.

import os

import pandas as pd
import psycopg
from dotenv import load_dotenv

# read DATABASE_URL from the .env file
load_dotenv()
database_url = os.getenv("DATABASE_URL")

def pinball_loss(real, forecast, percentile):
    too_low = (real - forecast).clip(lower=0)
    too_high = (forecast - real).clip(lower=0)
    return (percentile * too_low + (1 - percentile) * too_high).mean()

query = """
    SELECT city, permit_type, issued_date, wait_days
    FROM clean_permits
"""

connection = psycopg.connect(database_url)
rows = connection.execute(query).fetchall()
connection.close()

# turn the rows into a pandas table
columns = ["city", "permit_type", "issued_date", "wait_days"]
permits = pd.DataFrame(rows, columns=columns)
permits["issued_date"] = pd.to_datetime(permits["issued_date"])

# split on issued date, so slow permits aren't missing from the test months
cutoff = pd.Timestamp("2026-08-01")
train = permits[permits["issued_date"] < cutoff]
test = permits[permits["issued_date"] >= cutoff]

# the baseline only looks at the 90 days before the cutoff
recent = train[train["issued_date"] >= cutoff - pd.Timedelta(days=90)]

# score the baseline at each percentile
for percentile in [0.5, 0.8, 0.9]:
    forecasts = recent.groupby(["city", "permit_type"])["wait_days"].quantile(percentile)

    # put each permit's forecast next to its real wait
    forecast = forecasts.rename("forecast").reset_index()
    scored = test.merge(forecast, on=["city", "permit_type"], how="left")

    scored["covered"] = scored["wait_days"] <= scored["forecast"]

    # grade each city on its own
    for city in scored["city"].unique():
        one_city = scored[scored["city"] == city]
        print(city, pinball_loss(one_city["wait_days"], one_city["forecast"], percentile))

    print(percentile)
    print(scored["covered"].mean())
    print(scored.groupby("city")["covered"].mean())
    print(pinball_loss(scored["wait_days"], scored["forecast"], percentile))