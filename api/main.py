from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ml.forecast import forecast, permit_type_lists

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
)

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



@app.get("/permit-types")
def get_permit_types(
    city: str,

):
    city = city.lower()
    if city not in  permit_type_lists:
        raise HTTPException(status_code=400, detail=f"Unknown city: {city}")
    return permit_type_lists[city]