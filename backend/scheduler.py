import heapq
from dataclasses import dataclass, field

from models import EnergyTask, PricePoint, ScheduleResponse, TaskScheduleResult


@dataclass(order=True)
class _HeapTask:
    urgency: float
    task: EnergyTask = field(compare=False)


def _price_map(prices: list[PricePoint]) -> dict[int, float]:
    return {p.hour: p.price_per_kwh for p in prices}


def _window_cost(
    price_by_hour: dict[int, float],
    start: int,
    duration: int,
    power_kw: float,
) -> float | None:
    total = 0.0
    for h in range(start, start + duration):
        if h not in price_by_hour:
            return None
        total += price_by_hour[h] * power_kw
    return total


def find_best_window(
    task: EnergyTask,
    prices: list[PricePoint],
    load_profile: list[float] | None = None,
    max_kw: float = 100.0,
) -> tuple[int, float] | None:
    """
    Sliding-window search for the lowest-cost feasible start hour.
    """
    price_by_hour = _price_map(prices)
    if load_profile is None:
        load_profile = [0.0] * 24

    best_start: int | None = None
    best_cost = float("inf")

    latest_start = task.deadline - task.duration_hours
    if latest_start < task.earliest_start:
        return None

    for start in range(task.earliest_start, latest_start + 1):
        feasible = True
        for h in range(start, start + task.duration_hours):
            if h >= 24:
                feasible = False
                break
            if load_profile[h] + task.power_kw > max_kw:
                feasible = False
                break

        if not feasible:
            continue

        cost = _window_cost(price_by_hour, start, task.duration_hours, task.power_kw)
        if cost is not None and cost < best_cost:
            best_cost = cost
            best_start = start

    if best_start is None:
        return None
    return best_start, best_cost


def _fifo_start(task: EnergyTask) -> int | None:
    latest = task.deadline - task.duration_hours
    if latest < task.earliest_start:
        return None
    return task.earliest_start


def _apply_load(load_profile: list[float], task: EnergyTask, start: int) -> None:
    for h in range(start, start + task.duration_hours):
        if h < 24:
            load_profile[h] += task.power_kw


def optimize_schedule(
    tasks: list[EnergyTask],
    prices: list[PricePoint],
    max_household_kw: float,
    source: str = "csv_fallback",
) -> ScheduleResponse | None:
    """
    Greedy multi-task scheduler with min-heap ordering by deadline urgency.
    """
    price_by_hour = _price_map(prices)
    if not price_by_hour:
        return None

    heap: list[_HeapTask] = []
    for task in tasks:
        slack = (task.deadline - task.duration_hours) - task.earliest_start
        urgency = slack if slack >= 0 else -1.0
        heapq.heappush(heap, _HeapTask(urgency=urgency, task=task))

    load_profile = [0.0] * 24
    schedules: list[TaskScheduleResult] = []

    while heap:
        entry = heapq.heappop(heap)
        task = entry.task
        result = find_best_window(task, prices, load_profile, max_household_kw)
        if result is None:
            return None
        start, cost = result
        _apply_load(load_profile, task, start)
        schedules.append(
            TaskScheduleResult(
                task_id=task.id,
                name=task.name,
                start_hour=start,
                end_hour=start + task.duration_hours,
                cost=round(cost, 4),
            )
        )

    optimized_total = sum(s.cost for s in schedules)

    fifo_total = 0.0
    fifo_load = [0.0] * 24
    for task in tasks:
        start = _fifo_start(task)
        if start is None:
            return None
        for h in range(start, start + task.duration_hours):
            if fifo_load[h] + task.power_kw > max_household_kw:
                # FIFO may violate cap; still compute cost for comparison
                pass
            fifo_load[h] += task.power_kw
        cost = _window_cost(price_by_hour, start, task.duration_hours, task.power_kw)
        if cost is None:
            return None
        fifo_total += cost

    fifo_total = round(fifo_total, 4)
    optimized_total = round(optimized_total, 4)
    savings = round(max(0.0, fifo_total - optimized_total), 4)
    pct = round((savings / fifo_total * 100) if fifo_total > 0 else 0.0, 1)

    return ScheduleResponse(
        schedules=schedules,
        optimized_total_cost=optimized_total,
        fifo_total_cost=fifo_total,
        savings_dollars=savings,
        savings_percent=pct,
        source=source,
    )
