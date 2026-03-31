import { beforeEach, describe, expect, it, jest } from "@jest/globals";
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";

import LoginPage from "@/app/login/page";

jest.mock("@/lib/auth/session", () => ({
  getSessionToken: jest.fn(),
  setSessionToken: jest.fn(),
  clearSessionToken: jest.fn(),
}));

jest.mock("@/lib/api/auth", () => ({
  requestLocalDemoAccess: jest.fn(),
}));

describe("LoginPage", () => {
  beforeEach(async () => {
    jest.clearAllMocks();

    const { getSessionToken } = await import("@/lib/auth/session");
    const { requestLocalDemoAccess } = await import("@/lib/api/auth");

    (getSessionToken as jest.Mock).mockReturnValue(null);
    (requestLocalDemoAccess as jest.Mock).mockResolvedValue({
      access_token: "demo-token",
      token_type: "bearer",
      user_id: "00000000-0000-0000-0000-000000000002",
      email: "analyst@example.com",
      role: "data_analyst",
    });
  });

  it("stores the local demo token and reveals protected page links", async () => {
    const user = userEvent.setup();
    const { setSessionToken } = await import("@/lib/auth/session");

    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: /Use local analyst demo access/i }));

    await waitFor(() => {
      expect(setSessionToken).toHaveBeenCalledWith("demo-token");
    });

    expect(screen.getByText(/Local demo access is ready/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the forecasts page/i })).toBeInTheDocument();
  });

  it("shows the saved-session state when a token already exists", async () => {
    const { getSessionToken } = await import("@/lib/auth/session");
    (getSessionToken as jest.Mock).mockReturnValue("cached-token");

    render(<LoginPage />);

    expect(
      screen.getByText(/A saved browser session is already available/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the dashboard/i })).toBeInTheDocument();
  });

  it("shows a helpful error when the backend helper is unavailable", async () => {
    const user = userEvent.setup();
    const { requestLocalDemoAccess } = await import("@/lib/api/auth");
    (requestLocalDemoAccess as jest.Mock).mockRejectedValue(
      new Error("Local demo login is disabled"),
    );

    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: /Use local analyst demo access/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Local demo login is disabled");
    });
  });
});
