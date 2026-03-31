import { beforeEach, describe, expect, it, jest } from "@jest/globals";
import { render, screen, waitFor } from "@testing-library/react";

import DashboardPage from "@/app/dashboard/page";

jest.mock("@/lib/auth/session", () => ({
  getSessionToken: jest.fn(),
}));

jest.mock("@/lib/api/stores", () => ({
  getAccessibleStores: jest.fn(),
}));

jest.mock("@/lib/api/analytics", () => ({
  getDailyKPIs: jest.fn(),
}));

describe("DashboardPage", () => {
  beforeEach(async () => {
    jest.clearAllMocks();

    const { getSessionToken } = await import("@/lib/auth/session");
    const { getAccessibleStores } = await import("@/lib/api/stores");
    const { getDailyKPIs } = await import("@/lib/api/analytics");

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
    (getDailyKPIs as jest.Mock).mockResolvedValue({
      kpis: [
        {
          kpi_id: 11,
          store_id: 1,
          kpi_date: "2025-02-01",
          day_of_week: 6,
          total_sales: 1250,
          total_customers: 200,
          transactions: 180,
          avg_sales_per_transaction: 6.94,
          sales_per_customer: 6.25,
          is_promo_day: true,
          has_state_holiday: false,
          has_school_holiday: false,
          is_store_open: true,
        },
      ],
      count: 1,
      total: 1,
      summary: {
        total_records: 1,
        total_sales: 1250,
        total_customers: 200,
        avg_daily_sales: 1250,
        promo_days: 1,
        holiday_days: 0,
      },
    });
  });

  it("renders the authenticated dashboard flow", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Store Performance Dashboard")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/Performance Summary/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("heading", { name: "Total Sales" })).toBeInTheDocument();
    expect(screen.getByText(/Recent KPI Records/i)).toBeInTheDocument();
  });

  it("shows auth-required state without a token", async () => {
    const { getSessionToken } = await import("@/lib/auth/session");
    (getSessionToken as jest.Mock).mockReturnValue(null);

    render(<DashboardPage />);

    expect(screen.getByText("Authentication Required")).toBeInTheDocument();
    expect(screen.getByText(/Go to Login/i)).toBeInTheDocument();
  });

  it("shows a recoverable error when store loading fails", async () => {
    const { getAccessibleStores } = await import("@/lib/api/stores");
    (getAccessibleStores as jest.Mock).mockRejectedValue(new Error("Store API unavailable"));

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Connection Error")).toBeInTheDocument();
    });

    expect(screen.getByText("Store API unavailable")).toBeInTheDocument();
  });
});
