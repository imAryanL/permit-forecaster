# Chicago ingest: gets Chicago's building permits from the city's API,
# cleans each one to match our permits table, and saves them to Postgres.
# Grabs 1,000 permits at a time until there are none left.
# Permits already saved are skipped, so it's safe to run again.

import os

import psycopg
import requests
from dotenv import load_dotenv

# read DATABASE_URL from the .env file
load_dotenv()
database_url = os.getenv("DATABASE_URL")

url = "https://data.cityofchicago.org/resource/ydr8-5enu.json"

# how many permits to ask for in each request
page_size = 1000

# what we want back from Chicago
params = {
    "$select": "permit_,permit_type,review_type,work_description,reported_cost,application_start_date,issue_date",
    "$where": "issue_date >= '2023-01-01' AND application_start_date IS NOT NULL",
    "$limit": page_size,
    # same order every request, so pages never skip or repeat a permit
    "$order": "permit_",
}


# turn one Chicago permit into a row that matches permits table
def clean_permit(permit):
    cost = permit.get("reported_cost")
    if cost is not None:
        cost = float(cost)

    return {
        "city": "chicago",
        "permit_number": permit["permit_"],
        "permit_type": permit.get("permit_type"),
        "work_category": permit.get("review_type"),
        "description": permit.get("work_description"),
        "cost": cost,
        "applied_date": permit["application_start_date"][:10],
        "issued_date": permit["issue_date"][:10],
        # Chicago only lists permits that were already issued, so there is no status field
        "status": None,
    }


# python and Postgres cant communicate, psycopg will allow python to send SQL code to Postgres
connection = psycopg.connect(database_url)
cursor = connection.cursor()

# ON CONFLICT DO NOTHING skips permits we already saved
insert_sql = """
    INSERT INTO permits (city, permit_number, permit_type, work_category, description, cost, applied_date, issued_date, status)
    VALUES (%(city)s, %(permit_number)s, %(permit_type)s, %(work_category)s, %(description)s, %(cost)s, %(applied_date)s, %(issued_date)s, %(status)s)
    ON CONFLICT (city, permit_number) DO NOTHING
"""

offset = 0
total = 0
added = 0

# keep asking for the next page until Chicago sends back an empty one
while True:
    params["$offset"] = offset
    response = requests.get(url, params=params)
    # stop with a clear error if Chicago sends back an error instead of permits
    response.raise_for_status()
    permits = response.json()

    # an empty page means we got everything
    if len(permits) == 0:
        break

    for permit in permits:
        row = clean_permit(permit)
        cursor.execute(insert_sql, row)
        # rowcount is 1 if the permit was new, 0 if it was skipped as a duplicate
        added = added + cursor.rowcount

    connection.commit()
    total = total + len(permits)
    print("offset", offset, "done, fetched:", total, "new:", added)

    offset = offset + page_size

# write down this run in ingest_runs
cursor.execute(
    "INSERT INTO ingest_runs (city, rows_added, succeeded) VALUES (%s, %s, %s)",
    ("chicago", added, True),
)
connection.commit()

connection.close()

print("finished,", total, "permits fetched,", added, "new")
