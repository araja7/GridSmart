import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function formatHour(hour) {
  if (hour === 0) return "12a";
  if (hour < 12) return `${hour}a`;
  if (hour === 12) return "12p";
  return `${hour - 12}p`;
}

export default function PriceChart({ prices, schedules = [] }) {
  if (!prices?.length) {
    return <p className="empty-state">Loading price data…</p>;
  }

  const chartData = prices.map((p) => ({
    hour: p.hour,
    label: formatHour(p.hour),
    price: Number((p.price_per_kwh * 100).toFixed(2)),
    priceRaw: p.price_per_kwh,
  }));

  return (
    <>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#5b9fd4" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#5b9fd4" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a3544" vertical={false} />
          <XAxis
            dataKey="hour"
            type="number"
            domain={[0, 23]}
            ticks={[0, 3, 6, 9, 12, 15, 18, 21]}
            tickFormatter={formatHour}
            tick={{ fill: "#8b9cb3", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#8b9cb3", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            label={{ value: "¢/kWh", angle: -90, position: "insideLeft", fill: "#8b9cb3", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              background: "#1c2430",
              border: "1px solid #2a3544",
              borderRadius: 8,
              fontSize: 13,
            }}
            formatter={(value) => [`${value} ¢/kWh`, "Price"]}
            labelFormatter={(_, items) => {
              const hour = items?.[0]?.payload?.hour;
              return `Hour: ${formatHour(hour ?? 0)}`;
            }}
          />
          <Area
            type="monotone"
            dataKey="price"
            stroke="#5b9fd4"
            strokeWidth={2}
            fill="url(#priceGrad)"
          />
          {schedules.map((s, i) => (
            <ReferenceArea
              key={s.task_id}
              x1={s.start_hour}
              x2={s.end_hour}
              fill="#3dd68c"
              fillOpacity={0.15 + i * 0.05}
              stroke="#3dd68c"
              strokeOpacity={0.4}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
      <div className="chart-legend">
        <span>
          <span className="swatch" style={{ background: "#5b9fd4" }} />
          Grid price (Elecz)
        </span>
        {schedules.length > 0 && (
          <span>
            <span className="swatch" style={{ background: "#3dd68c" }} />
            Scheduled windows
          </span>
        )}
      </div>
    </>
  );
}
