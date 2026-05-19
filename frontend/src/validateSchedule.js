function taskLabel(task) {
  return (task.name || "").trim() || task.id || "Unnamed appliance";
}

export function normalizeTask(task) {
  return {
    ...task,
    power_kw: parseFloat(String(task.power_kw)),
    duration_hours: parseInt(String(task.duration_hours), 10),
    earliest_start: parseInt(String(task.earliest_start), 10),
    deadline: parseInt(String(task.deadline), 10),
  };
}

export function normalizeMaxKw(maxKw) {
  return parseFloat(String(maxKw));
}

/** @returns {string | null} User-facing error, or null if inputs look valid. */
export function validateScheduleInput(tasks, maxKw) {
  if (!tasks?.length) {
    return "Add at least one appliance to schedule.";
  }

  const maxHouseholdKw = normalizeMaxKw(maxKw);
  if (!Number.isFinite(maxHouseholdKw) || maxHouseholdKw <= 0) {
    return "Enter a valid max household power (kW) greater than 0.";
  }
  if (maxHouseholdKw > 100) {
    return "Max household power cannot exceed 100 kW.";
  }

  for (const raw of tasks) {
    const task = normalizeTask(raw);
    const name = taskLabel(task);

    if (!Number.isFinite(task.power_kw) || task.power_kw <= 0) {
      return `"${name}": enter a valid power (kW) greater than 0.`;
    }
    if (task.power_kw > 50) {
      return `"${name}": power cannot exceed 50 kW per device.`;
    }
    if (task.power_kw > maxHouseholdKw) {
      return `"${name}" uses ${task.power_kw} kW, which exceeds the ${maxHouseholdKw} kW household limit.`;
    }

    if (!Number.isInteger(task.duration_hours) || task.duration_hours < 1 || task.duration_hours > 12) {
      return `"${name}": duration must be between 1 and 12 hours.`;
    }

    if (!Number.isInteger(task.earliest_start) || task.earliest_start < 0 || task.earliest_start > 23) {
      return `"${name}": earliest start must be between 0 and 23.`;
    }

    if (!Number.isInteger(task.deadline) || task.deadline < 1 || task.deadline > 24) {
      return `"${name}": deadline must be between 1 and 24.`;
    }

    const available = task.deadline - task.earliest_start;
    if (task.duration_hours > available) {
      return `"${name}" needs ${task.duration_hours}h to run but only ${available}h is available between earliest start (hour ${task.earliest_start}) and deadline (hour ${task.deadline}).`;
    }

    if (task.earliest_start + task.duration_hours > 24) {
      return `"${name}" would run past midnight (starts at hour ${task.earliest_start} for ${task.duration_hours}h). Use an earlier start or shorter duration.`;
    }
  }

  return null;
}
