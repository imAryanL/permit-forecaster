from fastapi import FastAPI

from ml.forecast import forecast

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
    return forecast(city, permit_type, work_category, cost, description)