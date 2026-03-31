import { beforeEach, describe, expect, it, jest } from "@jest/globals";
import { render, screen, waitFor } from "@testing-library/react";

import ForecastsPage from "@/app/forecasts/page";
import { ApiError } from "@/lib/api/base-client";

jest.mock("@/lib/auth/session", () => ({
  getSessionToken: jest.fn(),
}));

jest.mock("@/lib/api/stores", () => ({
  getAccessibleStores: jest.fn(),
}));

jest.mock("@/lib/api/forecasts", () => ({
  getStoreForecasts: jest.fn(),
  getStoreWarnings: jest.fn(),
}));

describe("ForecastsPage", () => {
  beforeEach(async () => {
    jest.clearAllMocks();

    const { getSessionToken } = await import("@/lib/auth/session");
    const { getAccessibleStores } = await import("@/lib/api/stores");
    const { getStoreForecasts, getStoreWarnings } = await import("@/lib/api/forecasts");

    (getSessionToken as jest.Mock).mockReturnValue("mock-token");
    (getAccessibleStores as jest.Mock).mockResolvedValue({
      stores: [
        {
          store_id: 1,
          store_type: "A",
          assortment: "a",
          competition_distance: 100,
          promo2: true,
        },
      ],
      count: 1,
    });
    (getStoreForecasts as jest.Mock).mockResolvedValue({
      store_id: 1,
      model_type: "baseline",
      forecast_start_date: "2026-03-29",
      forecast_end_date: "2026-04-11",
      model_metadata: {
        model_id: "model-baseline-active",
        model_name: "baseline-demo",
        model_type: "baseline",
        version: "2026.03.28",
        is_active: true,
        published_at: "2026-03-28T10:00:00Z",
      },
      accuracy_metrics: {
        mape: 12.4,
        rmse: 845.2,
        mae: 602.8,
      },
      forecasts: [
        {
          forecast_date: "2026-03-29",
          predicted_sales: 5321,
          lower_bound: 4800,
          upper_bound: 5800,
          confidence_level: 95,
        },
      ],
      total: 1,
      offset: 0,
      limit: 100,
    });
    (getStoreWarnings as jest.Mock).mockResolvedValue([
      {
        store_id: 1,
        warning_type: "insufficient_history",
        warning_message: "Recent history is limited for this store",
        days_of_history: 42,
      },
    ]);
  });

  it("renders the authenticated forecast flow", async () => {
    render(<ForecastsPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Forecasts" })).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Accuracy Summary" })).toBeInTheDocument();
    });

    expect(screen.getByText(/baseline-demo/i)).toBeInTheDocument();
    expect(screen.getByText(/Warnings/i)).toBeInTheDocument();
    expect(screen.getByText(/Recent history is limited for this store/i)).toBeInTheDocument();
  });

  it("shows auth-required state without a token", async () => {
    const { getSessionToken } = await import("@/lib/auth/session");
    (getSessionToken as jest.Mock).mockReturnValue(null);

    render(<ForecastsPage />);

    expect(screen.getByText("Authentication Required")).toBeInTheDocument();
    expect(screen.getByText(/Go to Login/i)).toBeInTheDocument();
  });

  it("shows an empty state when no forecast has been published", async () => {
    const { getStoreForecasts, getStoreWarnings } = await import("@/lib/api/forecasts");
    (getStoreForecasts as jest.Mock).mockRejectedValue(
      new ApiError("No published forecasts found for store 1", 404, "not_found"),
    );
    (getStoreWarnings as jest.Mock).mockResolvedValue([]);

    render(<ForecastsPage />);

    await waitFor(() => {
      expect(screen.getByText("No Published Forecast")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Generate or publish forecasts through the backend first/i),
    ).toBeInTheDocument();
  });
});
