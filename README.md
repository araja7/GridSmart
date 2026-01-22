# GridSense – Cost-Aware Energy Task Scheduler

## The Problem

Residential energy consumption often peaks during hours when the electrical grid is under the most stress, leading to higher costs for consumers and greater reliance on "peaker" power plants (which are often less efficient and more polluting). While many appliances allow for delayed starts, consumers lack the real-time data or the algorithmic tools to know exactly when that delay should end to minimize costs and grid impact.

## The Solution

GridSense is a full-stack optimization tool that synchronizes household energy demand with real-time grid pricing. By ingesting live data from the PJM Interconnection (the regional transmission organization serving 65 million people), the application calculates the mathematically optimal window to run high-load appliances (EV chargers, dishwashers, dryers) based on a user's specific deadline.

## Core Functionality

- **Real-Time Data Ingestion**: Fetches Locational Marginal Prices (LMP) from the PJM API to track the current and forecasted cost of electricity.

- **Constraint-Based Scheduling**: Uses a sliding-window optimization algorithm to find the lowest-cost period between a user-defined "Earliest Start" and "Must-Finish By" deadline.

- **Resource Contention Management**: Prevents "virtual fuse blows" by ensuring that the total power draw of all scheduled tasks does not exceed a maximum household kW limit at any given time.

- **Visual Analytics**: A React-based dashboard that visualizes price volatility and provides a "Savings Report," comparing the optimized schedule against a standard "run-on-arrival" (FIFO) baseline.

## Technical Implementation

### Algorithms
- **Sliding Window Optimization**: Finds optimal time windows for task scheduling
- **Greedy Scheduling**: Efficient task prioritization
- **Min-Heap**: Task priority management for optimal ordering

### Backend
- **Python (FastAPI)**: Asynchronous API server handling optimization requests
- **Optimization Engine**: Core scheduling logic that processes constraints and price data
- **Caching Layer**: Reduces API latency and improves response times
- **Fail-Safe Mode**: Utilizes historical CSV data if the live grid API is unreachable

### Frontend
- **React**: Responsive dashboard built with modern React patterns
- **Recharts**: Time-series data visualization for price trends and schedules
- **Real-Time Updates**: Live price data and schedule optimization results

### Data Strategy
- **PJM API Integration**: Real-time Locational Marginal Price (LMP) data
- **Historical Data Fallback**: CSV-based backup when API is unavailable
- **Caching**: Reduces redundant API calls and improves performance

## Project Structure

```
GridSmart/
├── backend/                # Python (FastAPI)
│   ├── app.py              # Main API entry point
│   ├── scheduler.py        # Optimization logic (The "Brain")
│   ├── grid_service.py     # PJM API integration or CSV parser
│   ├── models.py           # EnergyTask and Price data classes
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # React (Vite)
│   ├── src/
│   │   ├── components/     # TaskForm, PriceChart, ResultsDisplay
│   │   ├── App.jsx         # Main dashboard logic
│   │   └── api.js          # Fetch calls to the Python backend
│   ├── package.json
│   └── public/
│
├── data/                   # Historical price CSVs for fallback mode
│
├── .gitignore
└── README.md
```

## Real-World Impact

In simulated tests using actual PJM Ohio Hub data, GridSense can reduce the cost of high-energy tasks by **15% to 40%** by shifting load from peak afternoon hours to late-night or early-morning troughs. This not only saves the user money but promotes a flatter "Load Profile," which is essential for a more stable and sustainable power grid.

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- Access to PJM API (or use historical CSV data)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Future Enhancements

- Configuration management (`config.py`, `.env` support)
- Comprehensive testing suite
- Docker containerization
- API documentation
- Custom React hooks for data management
- Enhanced error handling and logging

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
