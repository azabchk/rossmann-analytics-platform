import Link from "next/link";
import type { ReactNode } from "react";

export interface DashboardErrorStateProps {
  message: string;
  type?: "auth" | "permission" | "data" | "network" | "general";
  onRetry?: () => void;
  showDetails?: boolean;
  details?: string;
}

const errorMessages: Record<
  NonNullable<DashboardErrorStateProps["type"]>,
  { title: string; description: string }
> = {
  auth: {
    title: "Authentication Required",
    description: "Please log in to access the dashboard.",
  },
  permission: {
    title: "Access Denied",
    description: "You don't have permission to view this data.",
  },
  data: {
    title: "Data Not Available",
    description: "The requested data could not be found or loaded.",
  },
  network: {
    title: "Connection Error",
    description: "Unable to connect to the server. Please check your internet connection.",
  },
  general: {
    title: "Something Went Wrong",
    description: "An unexpected error occurred while loading the dashboard.",
  },
};

export default function DashboardErrorState({
  message,
  type = "general",
  onRetry,
  showDetails = false,
  details,
}: DashboardErrorStateProps): ReactNode {
  const errorInfo = errorMessages[type];

  return (
    <div className={`dashboard-error-state dashboard-error-state--${type}`}>
      <h2 className="error-title">{errorInfo.title}</h2>
      <p className="error-message">{message}</p>
      <p className="error-description">{errorInfo.description}</p>

      {showDetails && details && (
        <details className="error-details">
          <summary>Error Details</summary>
          <pre className="error-details-text">{details}</pre>
        </details>
      )}

      <div className="error-actions">
        {onRetry && (
          <button type="button" onClick={onRetry} className="retry-button">
            Try Again
          </button>
        )}
        {type === "auth" && (
          <Link href="/login" className="login-button">
            Go to Login
          </Link>
        )}
      </div>

      <div className="error-help">
        <h3>Need Help?</h3>
        <ul>
          <li>Check your internet connection</li>
          <li>Verify you have access to the requested store</li>
          <li>Try selecting a different date range</li>
          <li>Contact support if the problem persists</li>
        </ul>
      </div>
    </div>
  );
}

/**
 * Loading state component for dashboard.
 */
export interface DashboardLoadingStateProps {
  message?: string;
}

export function DashboardLoadingState({
  message = "Loading dashboard data...",
}: DashboardLoadingStateProps): ReactNode {
  return (
    <div className="dashboard-loading-state">
      <div className="loading-spinner" aria-label="Loading" />
      <p className="loading-message">{message}</p>
    </div>
  );
}

/**
 * Empty state component for dashboard.
 */
export interface DashboardEmptyStateProps {
  title?: string;
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function DashboardEmptyState({
  title = "No Data Available",
  message = "No data found for the selected filters.",
  action,
}: DashboardEmptyStateProps): ReactNode {
  return (
    <div className="dashboard-empty-state">
      <h2 className="empty-title">{title}</h2>
      <p className="empty-message">{message}</p>
      {action && (
        <button type="button" onClick={action.onClick} className="empty-action-button">
          {action.label}
        </button>
      )}
    </div>
  );
}
