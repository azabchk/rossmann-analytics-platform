import type { Metadata } from "next";

import DashboardClient from "@/features/dashboard/dashboard-client";

export const metadata: Metadata = {
  title: "Dashboard - Sales Forecasting Platform",
  description: "View store performance analytics and KPIs",
};

export default function DashboardPage() {
  return <DashboardClient />;
}
