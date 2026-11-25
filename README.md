# Permit Forecaster

Predicts how long a city takes to approve a building permit, using the city's own public permit records.

Work in progress. Cities: Orlando, Miami, Chicago, San Francisco and Austin (654,574 permits after cleaning).

The model beats a simple baseline by 18% on the typical wait and 24 to 27% on the slow cases. All the numbers are in [RESULTS.md](RESULTS.md), and the reason for every choice is in [DECISIONS.md](DECISIONS.md).

## Run the tests

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```
