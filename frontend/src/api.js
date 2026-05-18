const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchPrices() {
  const res = await fetch(`${API_BASE}/prices`);
  if (!res.ok) throw new Error("Failed to fetch prices");
  return res.json();
}

export async function scheduleTasks(payload) {
  const res = await fetch(`${API_BASE}/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Scheduling failed");
  }
  return res.json();
}
