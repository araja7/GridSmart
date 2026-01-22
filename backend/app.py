from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import EnergyTask, ScheduleRequest
from scheduler import optimize_schedule
from grid_service import get_current_prices

app = FastAPI(title="GridSense API")

#allow react frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], #default Vite port
    allow_methods=["*"],
    allow_headers=["*"],
)

#returns 24 hour price forecast for the dashboard chart
@app.get("/prices")
def read_prices():
    try:
        return get_current_prices
    except Exception as e:
        raise HTTPException(status_code = 500, detail = "Could not fetch grid data")

#receives a task and returns the optimal start time
@app.post("/schedule")
def schedule_task(request: ScheduleRequest):
    #get price data
    prices = get_current_prices()
    
    #run optimization algorithm
    result = optimize_schedule(request.task, prices)
    
    if not result:
        raise HTTPException(status_code = 400, detail = "No valid window found before deadline")
        
    return result
