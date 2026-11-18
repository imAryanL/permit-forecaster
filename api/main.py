from fastapi import FastAPI, HTTPException

from ml.forecast import forecast, permit_type_lists

app = FastAPI()


@app.get("/")
def hello():
    return {"message": "permit forecaster is running"}


@app.get("/forecast")
def get_forecast(
    city: str,
    permit_type: str,
    cost: float | None = None,
    work_category: str | None = None,
    description: str | None = None,
):
    city = city.lower()
    if city not in permit_type_lists:
        raise HTTPException(status_code=400, detail=f"Unknown city: {city}")
    return forecast(city, permit_type, work_category, cost, description)