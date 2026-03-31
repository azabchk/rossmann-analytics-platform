/**
 * Sales History Chart component.
 *
 * Displays historical sales data in a chart format.
 * This is a visualization component only - all data is provided by props.
 */

import type { ReactNode } from "react";

import type { DailyKPI } from "@/lib/api/analytics";

export interface SalesHistoryChartProps {
  kpis: DailyKPI[];
}

function formatCompactCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatShortDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export default function SalesHistoryChart({
  kpis,
}: SalesHistoryChartProps): ReactNode {
  const sortedKpis = [...kpis].sort((a, b) =>
    a.kpi_date.localeCompare(b.kpi_date)
  );

  const maxSales = Math.max(...sortedKpis.map((kpi) => kpi.total_sales || 0), 1);
  const chartHeight = 320;
  const chartWidth = 860;
  const padding = 48;
  const barWidth = Math.max(5, (chartWidth - 2 * padding) / sortedKpis.length - 2);

  const bars = sortedKpis.map((kpi, index) => {
    const x = padding + index * ((chartWidth - 2 * padding) / sortedKpis.length);
    const barHeight = ((kpi.total_sales || 0) / maxSales) * (chartHeight - 2 * padding);
    const y = chartHeight - padding - barHeight;

    const isSpecial = kpi.is_promo_day || kpi.has_state_holiday || kpi.has_school_holiday;
    const barColor = isSpecial ? "#d97706" : "#0f766e";

    return (
      <g key={kpi.kpi_id}>
        <rect
          x={x}
          y={y}
          width={barWidth}
          height={barHeight}
          fill={barColor}
          rx={2}
        />
        <title>
          {kpi.kpi_date}: ${(kpi.total_sales || 0).toLocaleString()} sales,{" "}
          {kpi.total_customers || 0} customers
          {kpi.is_promo_day && " - Promo"}
          {(kpi.has_state_holiday || kpi.has_school_holiday) && " - Holiday"}
        </title>
      </g>
    );
  });

  const yTicks = 5;
  const yAxisLabels = Array.from({ length: yTicks }, (_, i) => {
    const value = Math.round((maxSales / yTicks) * i);
    const y = chartHeight - padding - ((maxSales / yTicks) * i / maxSales) * (chartHeight - 2 * padding);
    return (
      <g key={i}>
        <line
          x1={padding}
          y1={y}
          x2={chartWidth - padding}
          y2={y}
          stroke="rgba(16, 36, 52, 0.12)"
          strokeDasharray="4"
        />
        <text x={padding - 10} y={y + 4} textAnchor="end" fontSize={12} fill="#5c7383">
          {formatCompactCurrency(value)}
        </text>
      </g>
    );
  });

  const xLabelIndices = sortedKpis.length <= 10
    ? sortedKpis.map((_, i) => i)
    : [0, Math.floor(sortedKpis.length / 2), sortedKpis.length - 1];

  const xAxisLabels = xLabelIndices.map((index) => {
    const kpi = sortedKpis[index];
    const x = padding + index * ((chartWidth - 2 * padding) / sortedKpis.length) + barWidth / 2;
    return (
      <text
        key={index}
        x={x}
        y={chartHeight - padding + 20}
        textAnchor="middle"
        fontSize={11}
        fill="#5c7383"
        transform={`rotate(-45, ${x}, ${chartHeight - padding + 20})`}
      >
        {formatShortDate(kpi.kpi_date)}
      </text>
    );
  });

  return (
    <div className="sales-history-chart">
      <div className="panel__header">
        <div className="section-heading">
          <h3>Sales History</h3>
          <p>Daily sales bars for the selected KPI window. Promo and holiday days are highlighted.</p>
        </div>
      </div>

      <div className="chart-frame">
        <svg width="100%" height={chartHeight} viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
          <line
            x1={padding}
            y1={padding}
            x2={padding}
            y2={chartHeight - padding}
            stroke="#8aa0af"
            strokeWidth={2}
          />

          <line
            x1={padding}
            y1={chartHeight - padding}
            x2={chartWidth - padding}
            y2={chartHeight - padding}
            stroke="#8aa0af"
            strokeWidth={2}
          />

          {yAxisLabels}
          {bars}
          {xAxisLabels}
        </svg>
      </div>

      <div className="chart-legend" aria-label="Sales chart legend">
        <span>
          <i className="legend-swatch legend-swatch--teal" />
          Normal day
        </span>
        <span>
          <i className="legend-swatch legend-swatch--amber" />
          Promo or holiday
        </span>
      </div>

      {sortedKpis.length > 7 && (
        <p className="chart-note">
          Label density is reduced automatically when the date range gets longer.
        </p>
      )}
    </div>
  );
}
