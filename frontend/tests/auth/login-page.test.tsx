import { beforeEach, describe, expect, it, jest } from "@jest/globals";
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";

import DemoLoginPanel from "@/features/auth/demo-login-panel";

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock("@/lib/auth/session", () => ({
  getSessionToken: jest.fn(),
  setSessionToken: jest.fn(),
  clearSessionToken: jest.fn(),
}));

jest.mock("@/lib/api/auth", () => ({
  requestLocalDemoAccess: jest.fn(),
  getCurrentUser: jest.fn(),
  signInWithLocalAccount: jest.fn(),
  signUpWithLocalAccount: jest.fn(),
}));

describe("LoginPage", () => {
  beforeEach(async () => {
    jest.clearAllMocks();

    const { getSessionToken } = await import("@/lib/auth/session");
    const {
      requestLocalDemoAccess,
      getCurrentUser,
      signInWithLocalAccount,
      signUpWithLocalAccount,
    } = await import("@/lib/api/auth");

    (getSessionToken as jest.Mock).mockReturnValue(null);
    (requestLocalDemoAccess as jest.Mock).mockResolvedValue({
      access_token: "demo-token",
      token_type: "bearer",
      user_id: "00000000-0000-0000-0000-000000000002",
      email: "analyst@example.com",
      role: "data_analyst",
    });
    (getCurrentUser as jest.Mock).mockResolvedValue({
      user_id: "00000000-0000-0000-0000-000000000002",
      email: "analyst@example.com",
      role: "data_analyst",
    });
    (signInWithLocalAccount as jest.Mock).mockResolvedValue({
      access_token: "account-token",
      token_type: "bearer",
      user_id: "00000000-0000-0000-0000-000000000003",
      email: "user@example.com",
      role: "data_analyst",
    });
    (signUpWithLocalAccount as jest.Mock).mockResolvedValue({
      access_token: "signup-token",
      token_type: "bearer",
      user_id: "00000000-0000-0000-0000-000000000004",
      email: "new-user@example.com",
      role: "data_analyst",
    });
  });

  it("stores the local demo token, validates it, and reveals protected page links", async () => {
    const user = userEvent.setup();
    const { setSessionToken } = await import("@/lib/auth/session");
    const { getCurrentUser } = await import("@/lib/api/auth");

    render(<DemoLoginPanel supabaseConfig={null} />);

    await user.click(screen.getByRole("button", { name: /Switch to demo access/i }));
    await user.click(screen.getByRole("button", { name: /Use local analyst demo access/i }));

    await waitFor(() => {
      expect(setSessionToken).toHaveBeenCalledWith("demo-token");
    });

    expect(getCurrentUser).toHaveBeenCalledWith({ accessToken: "demo-token" });
    expect(screen.getByText(/Local demo access is ready in this browser for analyst@example.com/i)).toBeInTheDocument();
    expect(screen.getByText("Authenticated email")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open the forecasts page/i })).toBeInTheDocument();
  });

  it("shows the saved-session state when a stored token is still valid", async () => {
    const { getSessionToken } = await import("@/lib/auth/session");
    (getSessionToken as jest.Mock).mockReturnValue("cached-token");

    render(<DemoLoginPanel supabaseConfig={null} />);

    await waitFor(() => {
      expect(screen.getByText("Authenticated email")).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: /Open the dashboard/i })).toBeInTheDocument();
  });

  it("shows a helpful error when the backend helper is unavailable", async () => {
    const user = userEvent.setup();
    const { requestLocalDemoAccess } = await import("@/lib/api/auth");
    (requestLocalDemoAccess as jest.Mock).mockRejectedValue(
      new Error("Local demo login is disabled"),
    );

    render(<DemoLoginPanel supabaseConfig={null} />);

    await user.click(screen.getByRole("button", { name: /Switch to demo access/i }));
    await user.click(screen.getByRole("button", { name: /Use local analyst demo access/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Local demo login is disabled");
    });
  });

  it("clears an invalid stored token and asks the user to sign in again", async () => {
    const { getSessionToken, clearSessionToken } = await import("@/lib/auth/session");
    const { getCurrentUser } = await import("@/lib/api/auth");
    (getSessionToken as jest.Mock).mockReturnValue("stale-token");
    (getCurrentUser as jest.Mock).mockRejectedValue(new Error("Token expired"));

    render(<DemoLoginPanel supabaseConfig={null} />);

    await waitFor(() => {
      expect(clearSessionToken).toHaveBeenCalled();
    });

    expect(
      screen.getByText(/Saved browser access expired or is invalid/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Switch to demo access/i }),
    ).toBeInTheDocument();
  });

  it("signs in with a real backend-owned local account flow", async () => {
    const user = userEvent.setup();
    const { getCurrentUser, signInWithLocalAccount } = await import("@/lib/api/auth");
    const { setSessionToken } = await import("@/lib/auth/session");

    (getCurrentUser as jest.Mock).mockResolvedValue({
      user_id: "00000000-0000-0000-0000-000000000004",
      email: "user@example.com",
      role: "data_analyst",
    });

    render(<DemoLoginPanel supabaseConfig={null} />);

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.type(screen.getByLabelText("Password"), "password-123");
    await user.click(screen.getByRole("button", { name: /Submit sign in/i }));

    await waitFor(() => {
      expect(signInWithLocalAccount).toHaveBeenCalledWith({
        email: "user@example.com",
        password: "password-123",
      });
    });

    expect(setSessionToken).toHaveBeenCalledWith("account-token");
    expect(getCurrentUser).toHaveBeenCalledWith({ accessToken: "account-token" });
    expect(screen.getByText(/Signed in successfully as user@example.com/i)).toBeInTheDocument();
  });

  it("creates an account through the backend-owned signup flow", async () => {
    const user = userEvent.setup();
    const { signUpWithLocalAccount, getCurrentUser } = await import("@/lib/api/auth");
    const { setSessionToken } = await import("@/lib/auth/session");

    (getCurrentUser as jest.Mock).mockResolvedValue({
      user_id: "00000000-0000-0000-0000-000000000004",
      email: "new-user@example.com",
      role: "data_analyst",
    });

    render(<DemoLoginPanel supabaseConfig={null} />);

    await user.click(screen.getByRole("button", { name: /Switch to sign up/i }));
    await user.type(screen.getByLabelText("Email"), "new-user@example.com");
    await user.type(screen.getByLabelText("Password"), "password-123");
    await user.type(screen.getByLabelText("Confirm password"), "password-123");
    await user.click(screen.getByRole("button", { name: /Submit sign up/i }));

    await waitFor(() => {
      expect(signUpWithLocalAccount).toHaveBeenCalledWith({
        email: "new-user@example.com",
        password: "password-123",
      });
    });

    expect(setSessionToken).toHaveBeenCalledWith("signup-token");
    expect(
      screen.getByText(/Account created successfully for new-user@example.com/i),
    ).toBeInTheDocument();
  });
});
