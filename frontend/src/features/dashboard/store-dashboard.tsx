"use client";

import type { ReactNode } from "react";

import SalesHistoryChart from "@/components/charts/sales-history-chart";
import DashboardErrorState, {
  DashboardEmptyState,
  DashboardLoadingState,
} from "@/features/dashboard/dashboard-error-state";
import StoreFilterForm from "@/features/dashboard/store-filter-form";
import type { DailyKPI, KPISummary } from "@/lib/api/analytics";
import type { Store } from "@/lib/api/stores";

export interface StoreDashboardProps {
  stores: Store[];
  selectedStoreId: number | null;
  startDate: string;
  endDate: string;
  dailyKpis: DailyKPI[];
  summary: KPISummary | null;
  isLoading: boolean;
  error: {
    message: string;
    type: "permission" | "data" | "network" | "general";
  } | null;
  onStoreSelect: (storeId: number | null) => void;
  onDateChange: (startDate: string, endDate: string) => void;
  onRetry: () => void;
}

function formatCurrency(value: number): string {
  return `$${Number(value).toLocaleString()}`;
}

export default function StoreDashboard({
  stores,
  selectedStoreId,
  startDate,
  endDate,
  dailyKpis,
  summary,
  isLoading,
  error,
  onStoreSelect,
  onDateChange,
  onRetry,
}: StoreDashboardProps): ReactNode {
  const selectedStore =
    stores.find((store) => store.store_id === selectedStoreId) ?? null;

  if (stores.length === 0 && !isLoading) {
    return (
      <section className="dashboard-page">
        <header className="dashboard-header">
          <h1>Store Performance Dashboard</h1>
          <p>
            Authorized analytics are served by the backend API and rendered here
            without frontend business rules.
          </p>
        </header>
        <DashboardEmptyState
          title="No Stores Available"
          message="This account does not currently have access to any stores."
        />
      </section>
    );
  }

  return (
    <section className="dashboard-page">
      <header className="dashboard-header">
        <h1>Store Performance Dashboard</h1>
        <p>
          Authorized KPI analytics for the selected store and date range. Access
          control, filtering, and aggregation remain in the FastAPI backend.
        </p>
      </header>

      <StoreFilterForm
        stores={stores}
        selectedStoreId={selectedStoreId}
        startDate={startDate}
        endDate={endDate}
        onStoreSelect={onStoreSelect}
        onDateChange={onDateChange}
      />

      {selectedStore ? (
        <section className="selected-store" aria-label="Selected store">
          <h2>Store {selectedStore.store_id}</h2>
          <p>
            Type {selectedStore.store_type}, assortment{" "}
            {selectedStore.assortment.toUpperCase()}, competition distance{" "}
            {selectedStore.competition_distance}m
            {selectedStore.promo2 ? ", Promo2 enabled" : ", Promo2 not enabled"}
          </p>
        </section>
      ) : (
        <DashboardEmptyState
          title="No Store Selected"
          message="Select one of the accessible stores to load KPI history."
        />
      )}

      {error ? (
        <DashboardErrorState
          message={error.message}
          type={error.type}
          onRetry={onRetry}
        />
      ) : null}

      {isLoading ? (
        <DashboardLoadingState message="Refreshing KPI data..." />
      ) : null}

      {summary ? (
        <section className="dashboard-summary" aria-label="KPI summary">
          <h2>Performance Summary</h2>
          <div className="summary-grid">
            <article className="summary-card">
              <h3>Total Sales</h3>
              <p>{formatCurrency(summary.total_sales)}</p>
            </article>
            <article className="summary-card">
              <h3>Total Customers</h3>
              <p>{summary.total_customers.toLocaleString()}</p>
            </article>
            <article className="summary-card">
              <h3>Average Daily Sales</h3>
              <p>{formatCurrency(summary.avg_daily_sales)}</p>
            </article>
            <article className="summary-card">
              <h3>Promotion Days</h3>
              <p>{summary.promo_days.toLocaleString()}</p>
            </article>
            <article className="summary-card">
              <h3>Holiday Days</h3>
              <p>{summary.holiday_days.toLocaleString()}</p>
            </article>
          </div>
        </section>
      ) : null}

      {dailyKpis.length > 0 ? (
        <section className="dashboard-data">
          <SalesHistoryChart kpis={dailyKpis} />
          <section aria-label="Recent KPI records">
            <h2>Recent KPI Records</h2>
            <table>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Sales</th>
                  <th scope="col">Customers</th>
                  <th scope="col">Transactions</th>
                </tr>
              </thead>
              <tbody>
                {dailyKpis.slice(0, 10).map((kpi) => (
                  <tr key={`${kpi.store_id}-${kpi.kpi_date}`}>
                    <td>{kpi.kpi_date}</td>
                    <td>{formatCurrency(kpi.total_sales)}</td>
                    <td>{kpi.total_customers.toLocaleString()}</td>
                    <td>{kpi.transactions.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </section>
      ) : null}

      {!isLoading && !error && selectedStoreId !== null && dailyKpis.length === 0 ? (
        <DashboardEmptyState
          title="No KPI Data"
          message="No KPI data is available for the selected store and date range."
        />
      ) : null}
    </section>
  );
}
