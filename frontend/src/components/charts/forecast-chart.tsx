"use client";

import type { ReactNode } from "react";

import type { ForecastPoint } from "@/lib/api/forecasts";

interface ForecastChartProps {
  forecastPoints: ForecastPoint[];
  historicalData?: Array<{ date: string; sales: number }>;
  height?: number;
  showLegend?: boolean;
}

export function ForecastChart({
  forecastPoints,
  historicalData,
  height = 320,
  showLegend = true,
}: ForecastChartProps): ReactNode {
  const width = 820;
  const padding = 48;

  const chartData = forecastPoints.map((point) => ({
    date: point.forecast_date,
    label: new Date(point.forecast_date).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    predicted: point.predicted_sales,
    lower: point.lower_bound ?? point.predicted_sales,
    upper: point.upper_bound ?? point.predicted_sales,
  }));

  if (historicalData?.length) {
    const lastHistoricalPoint = historicalData[historicalData.length - 1];
    chartData.unshift({
      date: lastHistoricalPoint.date,
      label: new Date(lastHistoricalPoint.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      predicted: lastHistoricalPoint.sales,
      lower: lastHistoricalPoint.sales,
      upper: lastHistoricalPoint.sales,
    });
  }

  if (chartData.length === 0) {
    return (
      <div className="forecast-chart-empty">
        <p>No forecast points are available for the selected store.</p>
      </div>
    );
  }

  const maxValue = Math.max(...chartData.map((point) => point.upper), 1);
  const minValue = Math.min(...chartData.map((point) => point.lower), 0);
  const valueRange = Math.max(maxValue - minValue, 1);
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;

  function x(index: number): number {
    if (chartData.length === 1) {
      return width / 2;
    }
    return padding + (usableWidth * index) / (chartData.length - 1);
  }

  function y(value: number): number {
    return padding + usableHeight - ((value - minValue) / valueRange) * usableHeight;
  }

  const predictionPath = chartData
    .map((point, index) => `${index === 0 ? "M" : "L"} ${x(index)} ${y(point.predicted)}`)
    .join(" ");

  const upperPath = chartData
    .map((point, index) => `${index === 0 ? "M" : "L"} ${x(index)} ${y(point.upper)}`)
    .join(" ");
  const lowerPath = [...chartData]
    .reverse()
    .map((point, reverseIndex) => {
      const index = chartData.length - reverseIndex - 1;
      return `L ${x(index)} ${y(point.lower)}`;
    })
    .join(" ");
  const bandPath = `${upperPath} ${lowerPath} Z`;

  const yAxisTicks = Array.from({ length: 5 }, (_, index) => {
    const ratio = index / 4;
    return {
      value: Math.round(maxValue - ratio * valueRange),
      y: padding + usableHeight * ratio,
    };
  });

  return (
    <div className="forecast-chart" style={{ height }}>
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} role="img">
        <title>Published forecast chart</title>

        {yAxisTicks.map((tick) => (
          <g key={tick.y}>
            <line
              x1={padding}
              y1={tick.y}
              x2={width - padding}
              y2={tick.y}
              stroke="#d1d5db"
              strokeDasharray="4 4"
            />
            <text x={padding - 8} y={tick.y + 4} textAnchor="end" fontSize="11" fill="#4b5563">
              {tick.value.toLocaleString()}
            </text>
          </g>
        ))}

        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={height - padding}
          stroke="#6b7280"
        />
        <line
          x1={padding}
          y1={height - padding}
          x2={width - padding}
          y2={height - padding}
          stroke="#6b7280"
        />

        <path d={bandPath} fill="rgba(59, 130, 246, 0.16)" stroke="none" />
        <path d={predictionPath} fill="none" stroke="#2563eb" strokeWidth="3" />

        {chartData.map((point, index) => (
          <g key={`${point.date}-${index}`}>
            <circle cx={x(index)} cy={y(point.predicted)} r="4" fill="#1d4ed8" />
            <title>
              {point.date}: {Math.round(point.predicted).toLocaleString()} predicted sales
            </title>
          </g>
        ))}

        {chartData.map((point, index) => (
          <text
            key={point.date}
            x={x(index)}
            y={height - padding + 20}
            textAnchor="middle"
            fontSize="11"
            fill="#4b5563"
          >
            {point.label}
          </text>
        ))}
      </svg>

      {showLegend ? (
        <div className="forecast-chart-legend">
          <p>Blue line: predicted sales</p>
          <p>Shaded band: lower and upper forecast bounds</p>
        </div>
      ) : null}
    </div>
  );
}

export function MultiStoreForecastChart({
  forecasts,
  height = 240,
}: {
  forecasts: Array<{ storeId: number; points: ForecastPoint[] }>;
  height?: number;
}): ReactNode {
  return (
    <div style={{ height }}>
      <h3>Forecast Overview</h3>
      <ul>
        {forecasts.map((forecast) => (
          <li key={forecast.storeId}>
            Store {forecast.storeId}: {forecast.points.length} forecast points
          </li>
        ))}
      </ul>
    </div>
  );
}
