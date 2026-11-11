# Forecast: loads the saved models and lists, and forecasts one permit's wait.

import joblib
import pandas as pd

# load everything once, when the file starts, so each forecast is fast
models = {
    50: joblib.load("models/model_50.joblib"),
    80: joblib.load("models/model_80.joblib"),
    90: joblib.load("models/model_90.joblib"),
}
top_60_lists = joblib.load("models/top_60_descriptions.joblib")
permit_type_lists = joblib.load("models/permit_types.joblib")
work_category_lists = joblib.load("models/work_categories.joblib")


def build_clues(city, permit_type, work_category, cost, description):
    # same as training: a blank description means "no number", not 0
    if description is None or description.strip() == "":
        description_words = None
    else:
        description_words = len(description.split())
    # same as training: trimmed, uppercase, and only kept if it is common in that city
    if description is None:
        common_description = "OTHER"
    else:
        common_description = description.strip().upper()
        if common_description not in top_60_lists[city]:
            common_description = "OTHER"
    # same as training: a type or category this city rarely uses becomes OTHER,
    # but a missing work category stays missing
    if permit_type not in permit_type_lists[city]:
        permit_type = "OTHER"
    if work_category is not None and work_category not in work_category_lists[city]:
        work_category = "OTHER"

    # one row, same columns and same order the model trained on
    clues = pd.DataFrame([{
        "city": city,
        "permit_type": permit_type,
        "work_category": work_category,
        "cost": float(cost) if cost is not None else None,
        "description_words": description_words,
        "common_description": common_description,
    }])

    # same as training: text clues are marked as categories
    for column in ["city", "permit_type", "work_category", "common_description"]:
        clues[column] = clues[column].astype("category")
    return clues


def forecast(city, permit_type, work_category, cost, description):
    clues = build_clues(city, permit_type, work_category, cost, description)

    # never below 0 days, and each slower case is at least the one before it
    fifty = max(0, models[50].predict(clues)[0])
    eighty = max(fifty, models[80].predict(clues)[0])
    ninety = max(eighty, models[90].predict(clues)[0])
    return {"50": round(fifty), "80": round(eighty), "90": round(ninety)}


# only runs when this file is run directly, not when the API imports it later
if __name__ == "__main__":
    print(forecast("miami", "BUILDING ROOFING", "Residential", 15000, "reroof"))
    print(forecast("orlando", "Mechanical Permit", None, 15000, None))