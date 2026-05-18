# GridSmart – Cost-Aware Energy Task Scheduler

## The Problem

Residential energy consumption often peaks during hours when the electrical grid is under the most stress, leading to higher costs for consumers and greater reliance on "peaker" power plants (which are often less efficient and more polluting). While many appliances allow for delayed starts, consumers lack the real-time data or the algorithmic tools to know exactly when that delay should end to minimize costs and grid impact.

## The Solution

GridSmart is a full-stack optimization tool that synchronizes household energy demand with real-time grid pricing. By ingesting live wholesale electricity prices from the [Elecz API](https://elecz.com/docs) (40+ countries, no API key required), the application calculates the mathematically optimal window to run high-load appliances (EV chargers, dishwashers, dryers) based on a user's specific deadline.

## Core Functionality

- **Real-Time Data Ingestion**: Fetches hourly spot prices from Elecz to track current and forecasted electricity costs for your chosen grid zone.

- **Constraint-Based Scheduling**: Uses a sliding-window optimization algorithm to find the lowest-cost period between a user-defined "Earliest Start" and "Must-Finish By" deadline.

- **Resource Contention Management**: Prevents "virtual fuse blows" by ensuring that the total power draw of all scheduled tasks does not exceed a maximum household kW limit at any given time.

- **Visual Analytics**: A React-based dashboard that visualizes price volatility and provides a "Savings Report," comparing the optimized schedule against a standard "run-on-arrival" (FIFO) baseline.

## Technical Implementation

### Algorithms
- **Sliding Window Optimization**: Finds optimal time windows for task scheduling
- **Greedy Scheduling**: Efficient multi-task prioritization
- **Min-Heap**: Task ordering by deadline urgency

### Backend
- **Python (FastAPI)**: API server on port 8000
- **Optimization Engine** (`scheduler.py`): Constraint and price processing
- **Caching Layer**: 5-minute in-memory cache for price data
- **Fail-Safe Mode**: Falls back to `data/ohio_hub_prices.csv` if Elecz is unreachable

### Frontend
- **React (Vite)**: Dashboard on port 5173
- **Recharts**: Time-series charts for prices and scheduled windows
- **Real-Time Updates**: Prices refresh every 60 seconds

### Data Strategy
- **Elecz API**: `GET https://elecz.com/signal/cheapest-hours` — no authentication required
- **Configurable zone**: Set `ELECZ_ZONE` (default `US-CA-SP15`) for CAISO, ERCOT, NYISO, ENTSO-E markets, and more
- **Historical CSV fallback**: Local Ohio Hub sample data when live fetch fails
- **Caching**: Reduces redundant API calls

## Project Structure

```
GridSmart/
├── backend/
│   ├── app.py              # FastAPI entry point
│   ├── scheduler.py        # Optimization logic
│   ├── grid_service.py     # Elecz API + CSV fallback
│   ├── models.py           # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # TaskForm, PriceChart, ResultsDisplay
│   │   ├── App.jsx
│   │   └── api.js
│   ├── package.json
│   └── public/
├── data/
│   └── ohio_hub_prices.csv # Fallback price curve
├── package.json            # Root scripts (npm run dev)
├── start.sh                # Alternative one-command launcher
├── .env.example
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/prices` | 24-hour price forecast (`source`: `elecz_api:{zone}` or `csv_fallback`) |
| `POST` | `/schedule` | Optimize task schedule (JSON body with `tasks` and `max_household_kw`) |

Interactive docs: **http://localhost:8000/docs**

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- Internet access (for Elecz live prices; CSV fallback works offline)

### Quick start (recommended)

From the project root, install everything once:

```bash
npm run install:all
```

Start both backend and frontend with a single command:

```bash
npm run dev
```

Then open **http://localhost:5173/** in your browser.

- Backend API: http://localhost:8000  
- Stop both servers with `Ctrl+C`

**Alternative** (without root npm):

```bash
./start.sh
```

### First-time setup (manual)

If you prefer separate terminals:

**Backend**
```bash
cd backend
python3 -m pip install -r requirements.txt
python3 app.py
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

### Configuration (optional)

Copy `.env.example` to `.env` in the project root to change the Elecz market zone:

```bash
cp .env.example .env
```

```env
ELECZ_ZONE=US-CA-SP15   # default — California (CAISO)
# ELECZ_ZONE=DE          # Germany (full 24h forecast)
# ELECZ_ZONE=US-TX-HB_HOUSTON
```

See [Elecz supported zones](https://elecz.com/docs) for all options. No API key is required.

### Verify the API

```bash
# Health
curl http://localhost:8000/health

# Prices (look for "source": "elecz_api:US-CA-SP15")
curl -s http://localhost:8000/prices | python3 -m json.tool

# Schedule
curl -s -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [{
      "id": "task-1",
      "name": "EV Charger",
      "power_kw": 7.2,
      "duration_hours": 4,
      "earliest_start": 18,
      "deadline": 24
    }],
    "max_household_kw": 10
  }' | python3 -m json.tool
```

If `/prices` returns `"source": "csv_fallback"`, Elecz was unreachable — the app still works using local CSV data. Restart the backend after killing any stale process on port 8000 (`lsof -i :8000`).

## Real-World Impact

By shifting high-load tasks into cheaper hours, GridSmart can reduce energy cost for scheduled appliances compared to running them as soon as they arrive (FIFO). Savings depend on the price curve for your zone; wholesale markets with strong day/night spreads (e.g. California, Germany) show the largest gains.

## Future Enhancements

- Comprehensive testing suite
- Docker containerization
- Custom React hooks for data management
- Enhanced error handling and logging
- Additional US zones and user location selection in the UI
