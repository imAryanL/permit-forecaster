# Miami ingest: gets Miami's building permits from the city's ArcGIS API,
# cleans each one to match our permits table, and saves them to Postgres.
# Grabs 2,000 permits at a time until there are none left.
# Permits already saved are skipped, so it's safe to run again.

import os
# datetime since Miami sends dates as milliseconds and not text
from datetime import datetime, timezone

import psycopg
import requests
from dotenv import load_dotenv

# read DATABASE_URL from the .env file
load_dotenv()
database_url = os.getenv("DATABASE_URL")

url = "https://services1.arcgis.com/CvuPhqcTQpZPT9qY/arcgis/rest/services/Building_Permits_Since_2014/FeatureServer/0/query"

# how many permits to ask for in each request (Miami allows up to 2,000)
page_size = 2000

# what we want back from Miami
# ArcGIS uses different names than Orlando and Chicago, but they do the same jobs:
# where = $where, outFields = $select, orderByFields = $order, resultRecordCount = $limit
params = {
    "where": "IssuedDate >= DATE '2023-01-01' AND PlanCreatedDate IS NOT NULL",
    "outFields": "PermitNumber,ScopeofWork,PropertyType,WorkItems,TotalCost,PlanCreatedDate,IssuedDate,BuildingPermitStatusDescription",
    "resultRecordCount": page_size,
    # same order every request, so pages never skip or repeat a permit
    "orderByFields": "ObjectId",
    # ask for plain JSON back
    "f": "json",
}


# turn Miami's milliseconds (like 1792148220000) into a date (like "2026-10-16")
def ms_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


# turn one Miami permit into a row that matches permits table
def clean_permit(permit):
    cost = permit.get("TotalCost")
    if cost is not None:
        cost = float(cost)

    return {
        "city": "miami",
        "permit_number": permit["PermitNumber"],
        "permit_type": permit.get("ScopeofWork"),
        "work_category": permit.get("PropertyType"),
        "description": permit.get("WorkItems"),
        "cost": cost,
        "applied_date": ms_to_date(permit["PlanCreatedDate"]),
        "issued_date": ms_to_date(permit["IssuedDate"]),
        "status": permit.get("BuildingPermitStatusDescription"),
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

# keep asking for the next page until Miami sends back an empty one
while True:
    params["resultOffset"] = offset
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # ArcGIS sends errors back as normal 200 responses, so check for them ourselves
    if "error" in data:
        raise Exception(data["error"])

    # the permits are inside "features", and each one keeps its fields in "attributes"
    permits = data["features"]

    # an empty page means we got everything
    if len(permits) == 0:
        break

    for feature in permits:
        row = clean_permit(feature["attributes"])
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
    ("miami", added, True),
)
connection.commit()

connection.close()

print("finished,", total, "permits fetched,", added, "new")
