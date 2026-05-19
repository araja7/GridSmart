function emptyTask(index) {
  return {
    id: `task-${index}`,
    name: "EV Charger",
    power_kw: 7.2,
    duration_hours: 4,
    earliest_start: 18,
    deadline: 24,
  };
}

export default function TaskForm({
  tasks,
  setTasks,
  maxKw,
  setMaxKw,
  onSubmit,
  loading,
}) {
  const updateTask = (index, field, value) => {
    setTasks((prev) =>
      prev.map((t, i) =>
        i === index ? { ...t, [field]: field === "name" ? value : Number(value) } : t
      )
    );
  };

  const addTask = () => {
    setTasks((prev) => [...prev, emptyTask(prev.length + 1)]);
  };

  const removeTask = (index) => {
    if (tasks.length <= 1) return;
    setTasks((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="card">
      <h2>Schedule Tasks</h2>

      <div className="kw-limit">
        <label>
          Max household power (kW)
          <input
            type="number"
            min={1}
            max={100}
            step={0.5}
            value={maxKw}
            onChange={(e) => setMaxKw(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="task-list">
        {tasks.map((task, index) => (
          <div key={task.id} className="task-item">
            <div className="task-item-header">
              <strong>{task.name || `Task ${index + 1}`}</strong>
              {tasks.length > 1 && (
                <button type="button" className="btn-remove" onClick={() => removeTask(index)}>
                  Remove
                </button>
              )}
            </div>

            <div className="form-row">
              <label>
                Device name
                <input
                  type="text"
                  value={task.name}
                  placeholder="e.g. EV Charger"
                  onChange={(e) => updateTask(index, "name", e.target.value)}
                />
              </label>
              <label>
                Power (kW)
                <input
                  type="number"
                  min={0.1}
                  step={0.1}
                  value={task.power_kw}
                  onChange={(e) => updateTask(index, "power_kw", e.target.value)}
                />
              </label>
            </div>

            <div className="form-row">
              <label>
                Duration (hrs)
                <input
                  type="number"
                  min={1}
                  max={12}
                  value={task.duration_hours}
                  onChange={(e) => updateTask(index, "duration_hours", e.target.value)}
                />
              </label>
              <label>
                Earliest start (hour)
                <input
                  type="number"
                  min={0}
                  max={23}
                  value={task.earliest_start}
                  onChange={(e) => updateTask(index, "earliest_start", e.target.value)}
                />
              </label>
            </div>

            <div className="form-row">
              <label>
                Must finish by (hour)
                <input
                  type="number"
                  min={1}
                  max={24}
                  value={task.deadline}
                  onChange={(e) => updateTask(index, "deadline", e.target.value)}
                />
              </label>
            </div>
          </div>
        ))}
      </div>

      <button type="button" className="btn btn-secondary" onClick={addTask}>
        + Add appliance
      </button>

      <button type="button" className="btn btn-primary" onClick={onSubmit} disabled={loading}>
        {loading ? "Optimizing…" : "Optimize schedule"}
      </button>
    </div>
  );
}
