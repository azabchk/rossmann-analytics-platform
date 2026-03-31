"use client";

import { useEffect, useState } from "react";

import DashboardErrorState, {
  DashboardLoadingState,
} from "@/features/dashboard/dashboard-error-state";
import StoreDashboard from "@/features/dashboard/store-dashboard";
import { ApiError } from "@/lib/api/base-client";
import { getDailyKPIs, type DailyKPI, type KPIListResponse } from "@/lib/api/analytics";
import { getSessionToken } from "@/lib/auth/session";
import { getAccessibleStores, type Store } from "@/lib/api/stores";

type DashboardState = {
  stores: Store[];
  selectedStoreId: number | null;
  kpis: KPIListResponse | null;
  isLoading: boolean;
  error: {
    message: string;
    type: "permission" | "data" | "network" | "general";
  } | null;
  requiresAuth: boolean;
};

function getDefaultStartDate(): string {
  const date = new Date();
  date.setDate(date.getDate() - 30);
  return date.toISOString().split("T")[0];
}

function getDefaultEndDate(): string {
  return new Date().toISOString().split("T")[0];
}

function isDailyKpi(kpi: KPIListResponse["kpis"][number]): kpi is DailyKPI {
  return "kpi_date" in kpi;
}

function toDashboardError(
  error: unknown,
  fallbackMessage: string,
): DashboardState["error"] {
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

export default function DashboardClient() {
  const [startDate, setStartDate] = useState(getDefaultStartDate);
  const [endDate, setEndDate] = useState(getDefaultEndDate);
  const [state, setState] = useState<DashboardState>({
    stores: [],
    selectedStoreId: null,
    kpis: null,
    isLoading: true,
    error: null,
    requiresAuth: false,
  });

  useEffect(() => {
    void initializeDashboard();
  }, []);

  async function initializeDashboard(): Promise<void> {
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
      const kpis =
        initialStoreId === null
          ? { kpis: [], count: 0, total: 0, summary: undefined }
          : await getDailyKPIs({
              store_id: initialStoreId,
              start_date: startDate,
              end_date: endDate,
            });

      setState({
        stores: storeResponse.stores,
        selectedStoreId: initialStoreId,
        kpis,
        isLoading: false,
        error: null,
        requiresAuth: false,
      });
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: toDashboardError(error, "Failed to load dashboard data"),
      }));
    }
  }

  async function loadKpis(
    storeId: number,
    nextStartDate: string,
    nextEndDate: string,
  ): Promise<void> {
    setState((prev) => ({
      ...prev,
      isLoading: true,
      error: null,
    }));

    try {
      const response = await getDailyKPIs({
        store_id: storeId,
        start_date: nextStartDate,
        end_date: nextEndDate,
      });

      setState((prev) => ({
        ...prev,
        kpis: response,
        isLoading: false,
      }));
    } catch (error) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: toDashboardError(error, "Failed to load KPI data"),
      }));
    }
  }

  function handleStoreSelect(storeId: number | null): void {
    setState((prev) => ({
      ...prev,
      selectedStoreId: storeId,
      kpis: storeId === null ? { kpis: [], count: 0 } : prev.kpis,
    }));

    if (storeId !== null) {
      void loadKpis(storeId, startDate, endDate);
    }
  }

  function handleDateChange(nextStartDate: string, nextEndDate: string): void {
    setStartDate(nextStartDate);
    setEndDate(nextEndDate);

    if (state.selectedStoreId !== null) {
      void loadKpis(state.selectedStoreId, nextStartDate, nextEndDate);
    }
  }

  if (state.requiresAuth) {
    return (
      <DashboardErrorState
        message="Sign in first so the dashboard can call the protected backend APIs."
        type="auth"
      />
    );
  }

  if (state.isLoading && state.stores.length === 0) {
    return <DashboardLoadingState message="Loading accessible stores..." />;
  }

  if (state.error && state.stores.length === 0) {
    return (
      <DashboardErrorState
        message={state.error.message}
        type={state.error.type}
        onRetry={() => {
          void initializeDashboard();
        }}
      />
    );
  }

  const dailyKpis = state.kpis?.kpis.filter(isDailyKpi) ?? [];
  return (
    <StoreDashboard
      stores={state.stores}
      selectedStoreId={state.selectedStoreId}
      startDate={startDate}
      endDate={endDate}
      dailyKpis={dailyKpis}
      summary={state.kpis?.summary ?? null}
      isLoading={state.isLoading}
      error={state.error}
      onStoreSelect={handleStoreSelect}
      onDateChange={handleDateChange}
      onRetry={() => {
        if (state.selectedStoreId !== null) {
          void loadKpis(state.selectedStoreId, startDate, endDate);
          return;
        }
        void initializeDashboard();
      }}
    />
  );
}
