from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from grid_service import get_current_prices
from models import PricesResponse, ScheduleRequest
from scheduler import optimize_schedule

app = FastAPI(
    title="GridSmart API",
    description="Cost-aware energy task scheduler using Elecz grid pricing",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/prices", response_model=PricesResponse)
def read_prices():
    try:
        prices, source, cached = get_current_prices()
        return PricesResponse(prices=prices, source=source, cached=cached)
    except Exception:
        raise HTTPException(status_code=500, detail="Could not fetch grid data")


@app.post("/schedule")
def schedule_tasks(request: ScheduleRequest):
    try:
        prices, source, _ = get_current_prices()
    except Exception:
        raise HTTPException(status_code=500, detail="Could not fetch grid data")

    result = optimize_schedule(
        request.tasks,
        prices,
        request.max_household_kw,
        source=source,
    )

    if not result:
        raise HTTPException(
            status_code=400,
            detail="No valid schedule found within deadlines and power limits",
        )

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
