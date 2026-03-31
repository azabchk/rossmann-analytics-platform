"use client";

import { useEffect, useState } from "react";

import { ForecastChart } from "@/components/charts/forecast-chart";
import DashboardErrorState, {
  DashboardEmptyState,
  DashboardLoadingState,
} from "@/features/dashboard/dashboard-error-state";
import { ApiError } from "@/lib/api/base-client";
import type { LowDataWarning, PublishedForecastResponse } from "@/lib/api/forecasts";
import { getStoreForecasts, getStoreWarnings } from "@/lib/api/forecasts";
import { getSessionToken } from "@/lib/auth/session";
import { getAccessibleStores, type Store } from "@/lib/api/stores";

type ForecastPageState = {
  stores: Store[];
  selectedStoreId: number | null;
  forecast: PublishedForecastResponse | null;
  warnings: LowDataWarning[];
  isLoading: boolean;
  error: {
    message: string;
    type: "permission" | "data" | "network" | "general";
  } | null;
  requiresAuth: boolean;
};

function toForecastError(
  error: unknown,
  fallbackMessage: string,
): ForecastPageState["error"] {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return { message: error.message, type: "permission" };
    }
    if (error.status >= 500) {
      return { message: error.message, type: "network" };
    }
    return { message: error.message, type: "data" };
  }

  if (error instanceof Error) {
    return { message: error.message, type: "network" };
  }

  return { message: fallbackMessage, type: "general" };
}

function formatMetric(metric: number | null | undefined): string {
  if (metric === undefined || metric === null) {
    return "N/A";
  }
  return metric.toFixed(2);
}

function getAccuracyTone(mape: number | null | undefined): "strong" | "moderate" | "low" {
  if (mape === undefined || mape === null) {
    return "moderate";
  }
  if (mape < 10) {
    return "strong";
  }
  if (mape < 15) {
    return "moderate";
  }
  return "low";
}

export default function ForecastView() {
  const [state, setState] = useState<ForecastPageState>({
    stores: [],
    selectedStoreId: null,
    forecast: null,
    warnings: [],
    isLoading: true,
    error: null,
    requiresAuth: false,
  });

  useEffect(() => {
    void initializeForecastWorkspace();
  }, []);

  async function initializeForecastWorkspace(): Promise<void> {
    const token = getSessionToken();
    if (!token) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        requiresAuth: true,
        error: null,
      }));
      return;
    }

    setState((prev) => ({
      ...prev,
      isLoading: true,
      requiresAuth: false,
      error: null,
    }));

    try {
      const storeResponse = await getAccessibleStores();
      const initialStoreId = storeResponse.stores[0]?.store_id ?? null;

      setState({
        stores: storeResponse.stores,
        selectedStoreId: initialStoreId,
        forecast: null,
        warnings: [],
        isLoading: false,
        error: null,
        requiresAuth: false,
      });

      if (initialStoreId !== null) {
        await loadForecast(initialStoreId);
      }
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: toForecastError(error, "Failed to load accessible stores"),
      }));
    }
  }

  async function loadForecast(storeId: number): Promise<void> {
    setState((prev) => ({
      ...prev,
      isLoading: true,
      error: null,
    }));

    try {
      const warnings = await getStoreWarnings(storeId);
      let forecast: PublishedForecastResponse | null = null;

      try {
        forecast = await getStoreForecasts(storeId);
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 404)) {
          throw error;
        }
      }

      setState((prev) => ({
        ...prev,
        forecast,
        warnings,
        isLoading: false,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: toForecastError(error, "Failed to load forecasts"),
      }));
    }
  }

  if (state.requiresAuth) {
    return (
      <DashboardErrorState
        message="Sign in first so the frontend can request protected forecast data."
        type="auth"
      />
    );
  }

  if (state.isLoading && state.stores.length === 0) {
    return <DashboardLoadingState message="Loading forecast workspace..." />;
  }

  if (state.error && state.stores.length === 0) {
    return (
      <DashboardErrorState
        message={state.error.message}
        type={state.error.type}
        onRetry={() => {
          void initializeForecastWorkspace();
        }}
      />
    );
  }

  return (
    <section className="forecast-page">
      <header>
        <h1>Forecasts</h1>
        <p>
          Published forecasts are exposed through FastAPI only. The browser does
          not talk to Supabase directly.
        </p>
      </header>

      <div className="forecast-controls">
        <label htmlFor="forecast-store-select">Store</label>
        <select
          id="forecast-store-select"
          value={state.selectedStoreId ?? ""}
          disabled={state.stores.length === 0}
          onChange={(event) => {
            const nextStoreId = event.target.value ? Number(event.target.value) : null;
            setState((prev) => ({
              ...prev,
              selectedStoreId: nextStoreId,
              forecast: nextStoreId === null ? null : prev.forecast,
              warnings: nextStoreId === null ? [] : prev.warnings,
            }));

            if (nextStoreId !== null) {
              void loadForecast(nextStoreId);
            }
          }}
        >
          <option value="">Select a store...</option>
          {state.stores.map((store) => (
            <option key={store.store_id} value={store.store_id}>
              Store {store.store_id} - Type {store.store_type}
            </option>
          ))}
        </select>
      </div>

      {state.isLoading ? (
        <DashboardLoadingState message="Loading published forecast..." />
      ) : null}

      {state.error && state.stores.length > 0 ? (
        <DashboardErrorState
          message={state.error.message}
          type={state.error.type}
          onRetry={() => {
            if (state.selectedStoreId !== null) {
              void loadForecast(state.selectedStoreId);
            }
          }}
        />
      ) : null}

      {state.forecast ? (
        <>
          <section className="forecast-summary">
            <h2>Store {state.forecast.store_id} Forecast</h2>
            <p>
              Forecast window: {state.forecast.forecast_start_date} to{" "}
              {state.forecast.forecast_end_date}
            </p>
            <p>
              Model: {state.forecast.model_metadata.model_name} (
              {state.forecast.model_metadata.model_type})
            </p>
            <p>Version: {state.forecast.model_metadata.version}</p>
            <p>Published at: {state.forecast.model_metadata.published_at}</p>
            {state.forecast.accuracy_metrics ? (
              <section
                className={`forecast-accuracy forecast-accuracy--${getAccuracyTone(
                  state.forecast.accuracy_metrics.mape,
                )}`}
                aria-label="Accuracy summary"
              >
                <h3>Accuracy Summary</h3>
                <p>MAPE: {formatMetric(state.forecast.accuracy_metrics.mape)}%</p>
                <p>RMSE: {formatMetric(state.forecast.accuracy_metrics.rmse)}</p>
                <p>MAE: {formatMetric(state.forecast.accuracy_metrics.mae)}</p>
              </section>
            ) : null}
          </section>

          <ForecastChart forecastPoints={state.forecast.forecasts} />

          <section className="forecast-table">
            <h2>Forecast Points</h2>
            <table>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Predicted Sales</th>
                  <th scope="col">Lower Bound</th>
                  <th scope="col">Upper Bound</th>
                </tr>
              </thead>
              <tbody>
                {state.forecast.forecasts.map((point) => (
                  <tr key={point.forecast_date}>
                    <td>{point.forecast_date}</td>
                    <td>{Math.round(point.predicted_sales).toLocaleString()}</td>
                    <td>
                      {Math.round(point.lower_bound ?? point.predicted_sales).toLocaleString()}
                    </td>
                    <td>
                      {Math.round(point.upper_bound ?? point.predicted_sales).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : null}

      {!state.isLoading && !state.error && state.selectedStoreId !== null && !state.forecast ? (
        <DashboardEmptyState
          title="No Published Forecast"
          message="Generate or publish forecasts through the backend first, then reload this page."
        />
      ) : null}

      {state.warnings.length > 0 ? (
        <section className="forecast-warnings">
          <h2>Warnings</h2>
          <ul>
            {state.warnings.map((warning) => (
              <li key={`${warning.store_id}-${warning.warning_type}`}>
                Store {warning.store_id}: {warning.warning_message} (
                {warning.days_of_history} history days)
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
