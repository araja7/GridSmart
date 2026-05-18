import { useCallback, useEffect, useState } from "react";
import { fetchPrices, scheduleTasks } from "./api";
import PriceChart from "./components/PriceChart";
import ResultsDisplay from "./components/ResultsDisplay";
import TaskForm from "./components/TaskForm";

const DEFAULT_TASKS = [
  {
    id: "task-1",
    name: "EV Charger",
    power_kw: 7.2,
    duration_hours: 4,
    earliest_start: 18,
    deadline: 24,
  },
  {
    id: "task-2",
    name: "Dishwasher",
    power_kw: 1.8,
    duration_hours: 2,
    earliest_start: 20,
    deadline: 24,
  },
];

export default function App() {
  const [prices, setPrices] = useState([]);
  const [priceMeta, setPriceMeta] = useState({ source: "", cached: false, zone: "" });
  const [tasks, setTasks] = useState(DEFAULT_TASKS);
  const [maxKw, setMaxKw] = useState(10);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadPrices = useCallback(async () => {
    try {
      const data = await fetchPrices();
      setPrices(data.prices);
      const zone = data.source?.startsWith("elecz_api:")
        ? data.source.split(":")[1]
        : "";
      setPriceMeta({ source: data.source, cached: data.cached, zone });
      setError(null);
    } catch {
      setError("Could not load grid prices. Is the backend running on port 8000?");
    }
  }, []);

  useEffect(() => {
    loadPrices();
    const interval = setInterval(loadPrices, 60_000);
    return () => clearInterval(interval);
  }, [loadPrices]);

  const handleOptimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await scheduleTasks({ tasks, max_household_kw: maxKw });
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const sourceLabel = priceMeta.source?.startsWith("elecz_api:")
    ? `Elecz API · ${priceMeta.zone || "live"}`
    : "CSV fallback";

  return (
    <div className="app">
      <header className="header">
        <h1>GridSmart</h1>
        <p>Cost-aware energy task scheduler — shift load to the cheapest hours.</p>
        <span className={`badge ${priceMeta.source?.startsWith("elecz_api:") ? "live" : ""}`}>
          {priceMeta.source?.startsWith("elecz_api:") && <span className="dot" />}
          {sourceLabel}
          {priceMeta.cached && " · cached"}
        </span>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="grid">
        <div>
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <div className="refresh-row">
              <button type="button" className="btn-refresh" onClick={loadPrices}>
                Refresh prices
              </button>
            </div>
            <h2>24-Hour Price Forecast</h2>
            <PriceChart prices={prices} schedules={result?.schedules ?? []} />
          </div>

          <ResultsDisplay result={result} />
        </div>

        <TaskForm
          tasks={tasks}
          setTasks={setTasks}
          maxKw={maxKw}
          setMaxKw={setMaxKw}
          onSubmit={handleOptimize}
          loading={loading}
        />
      </div>
    </div>
  );
}
