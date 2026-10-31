# Baseline: the simple forecast the model has to beat.
# For each city and permit type, it predicts the median wait from recent
# permits, then scores that against newer permits it never saw.

import os

import pandas as pd
import psycopg
from dotenv import load_dotenv

# read DATABASE_URL from the .env file
load_dotenv()
database_url = os.getenv("DATABASE_URL")

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

# median wait for each city and permit type
medians = recent.groupby(["city", "permit_type"])["wait_days"].median()

# put each permit's forecast next to its real wait
forecast = medians.rename("forecast").reset_index()
test = test.merge(forecast, on=["city", "permit_type"], how="left")

# how many days off each forecast was
test["error"] = (test["wait_days"] - test["forecast"]).abs()

print(test["error"].mean())
print(test.groupby("city")["error"].mean())