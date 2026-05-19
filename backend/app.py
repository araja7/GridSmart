from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from grid_service import get_current_prices, require_live_prices
from models import PricePoint, PricesResponse, ScheduleRequest
from scheduler import diagnose_schedule_failure, optimize_schedule, validate_tasks

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


def _prices_response(bundle) -> PricesResponse:
    return PricesResponse(
        prices=bundle.prices,
        source=bundle.source,
        cached=bundle.cached,
        live=bundle.live,
        partial=bundle.partial,
        elecz_attempted=bundle.elecz_attempted,
        elecz_zone=bundle.elecz_zone,
        elecz_hours_returned=bundle.elecz_hours_returned,
        elecz_hours_real=bundle.elecz_hours_real,
        elecz_data_complete=bundle.elecz_data_complete,
        fallback_reason=bundle.fallback_reason,
        filled_hours=bundle.filled_hours,
    )


@app.get("/prices", response_model=PricesResponse)
def read_prices():
    try:
        return _prices_response(get_current_prices())
    except Exception:
        raise HTTPException(status_code=500, detail="Could not fetch grid data")


@app.post("/schedule")
def schedule_tasks(request: ScheduleRequest):
    try:
        bundle = get_current_prices()
        require_live_prices(bundle)
        prices: list[PricePoint] = bundle.prices
        source = bundle.source
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Could not fetch grid data")

    validation_error = validate_tasks(request.tasks, request.max_household_kw)
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    result = optimize_schedule(
        request.tasks,
        prices,
        request.max_household_kw,
        source=source,
    )

    if not result:
        detail = diagnose_schedule_failure(
            request.tasks,
            prices,
            request.max_household_kw,
        )
        raise HTTPException(status_code=400, detail=detail)

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
