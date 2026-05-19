const STORAGE_KEY = "gridsmart-state";

function isValidTask(task) {
  return (
    task &&
    typeof task.id === "string" &&
    typeof task.name === "string" &&
    Number.isFinite(Number(task.power_kw)) &&
    Number.isFinite(Number(task.duration_hours)) &&
    Number.isFinite(Number(task.earliest_start)) &&
    Number.isFinite(Number(task.deadline))
  );
}

export function loadPersistedState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;

    const data = JSON.parse(raw);
    if (!Array.isArray(data.tasks) || data.tasks.length === 0) return null;
    if (!data.tasks.every(isValidTask)) return null;

    const maxKw = Number(data.maxKw);
    if (!Number.isFinite(maxKw) || maxKw <= 0) return null;

    return {
      tasks: data.tasks,
      maxKw,
      result: data.result ?? null,
    };
  } catch {
    return null;
  }
}

export function savePersistedState({ tasks, maxKw, result }) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ tasks, maxKw, result: result ?? null })
    );
  } catch {
    // Ignore quota / private browsing errors
  }
}
