from pydantic import BaseModel, Field


class PricePoint(BaseModel):
    hour: int = Field(ge=0, le=23, description="Hour of day (0-23)")
    price_per_kwh: float = Field(description="Price in local currency per kWh")
    timestamp: str | None = None


class EnergyTask(BaseModel):
    id: str = Field(default="task-1")
    name: str = Field(default="Appliance")
    power_kw: float = Field(gt=0, le=50, description="Power draw in kW")
    duration_hours: int = Field(ge=1, le=12, description="How long the task runs")
    earliest_start: int = Field(ge=0, le=23, description="Earliest hour to start (0-23)")
    deadline: int = Field(ge=1, le=24, description="Must finish by this hour (1-24)")


class ScheduleRequest(BaseModel):
    tasks: list[EnergyTask] = Field(min_length=1)
    max_household_kw: float = Field(default=10.0, gt=0, le=100)


class TaskScheduleResult(BaseModel):
    task_id: str
    name: str
    start_hour: int
    end_hour: int
    cost: float


class ScheduleResponse(BaseModel):
    schedules: list[TaskScheduleResult]
    optimized_total_cost: float
    fifo_total_cost: float
    savings_dollars: float
    savings_percent: float
    source: str


class PricesResponse(BaseModel):
    prices: list[PricePoint]
    source: str
    cached: bool
