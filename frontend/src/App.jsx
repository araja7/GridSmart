import { useCallback, useEffect, useState } from "react";
import { fetchPrices, scheduleTasks } from "./api";
import { loadPersistedState, savePersistedState } from "./persistState";
import { normalizeMaxKw, normalizeTask, validateScheduleInput } from "./validateSchedule";
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

function zoneFromSource(source) {
  if (!source) return "";
  const parts = source.split(":");
  return parts.length > 1 ? parts.slice(1).join(":") : "";
}

function priceStatusLabel(meta) {
  const zone = meta.zone || zoneFromSource(meta.source);
  if (meta.live) {
    return `Elecz live · ${zone}`;
  }
  if (meta.partial) {
    const real = meta.elecz_hours_real ?? "?";
    return `Elecz partial · ${real}/24h · ${zone}`;
  }
  if (meta.source === "csv_fallback") {
    return "CSV fallback";
  }
  return meta.source || "Unknown source";
}

function badgeClass(meta) {
  if (meta.live) return "badge live";
  if (meta.partial) return "badge partial";
  return "badge";
}

const persisted = loadPersistedState();

export default function App() {
  const [prices, setPrices] = useState([]);
  const [priceMeta, setPriceMeta] = useState({
    source: "",
    cached: false,
    live: false,
    partial: false,
    zone: "",
    elecz_hours_real: null,
    fallback_reason: null,
  });
  const [tasks, setTasks] = useState(persisted?.tasks ?? DEFAULT_TASKS);
  const [maxKw, setMaxKw] = useState(persisted?.maxKw ?? 10);
  const [result, setResult] = useState(persisted?.result ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadPrices = useCallback(async () => {
    try {
      const data = await fetchPrices();
      setPrices(data.prices);
      setPriceMeta({
        source: data.source,
        cached: data.cached,
        live: data.live,
        partial: data.partial,
        zone: data.elecz_zone || zoneFromSource(data.source),
        elecz_hours_real: data.elecz_hours_real,
        fallback_reason: data.fallback_reason,
      });
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

  useEffect(() => {
    savePersistedState({ tasks, maxKw, result });
  }, [tasks, maxKw, result]);

  const handleOptimize = async () => {
    const validationError = validateScheduleInput(tasks, maxKw);
    if (validationError) {
      setError(validationError);
      setResult(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const payload = {
        tasks: tasks.map((t) => normalizeTask(t)),
        max_household_kw: normalizeMaxKw(maxKw),
      };
      const data = await scheduleTasks(payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const showLiveDot = priceMeta.live || priceMeta.partial;
  const statusHint =
    priceMeta.fallback_reason === "elecz_unavailable_serving_stale"
      ? " · stale cache"
      : priceMeta.fallback_reason && priceMeta.source === "csv_fallback"
        ? ` · ${priceMeta.fallback_reason.replaceAll("_", " ")}`
        : "";

  return (
    <div className="app">
      <header className="header">
        <h1>GridSmart</h1>
        <p>Cost-aware energy task scheduler — shift load to the cheapest hours.</p>
        <span className={badgeClass(priceMeta)} title={priceMeta.fallback_reason || undefined}>
          {showLiveDot && <span className="dot" />}
          {priceStatusLabel(priceMeta)}
          {priceMeta.cached && " · cached"}
          {statusHint}
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
