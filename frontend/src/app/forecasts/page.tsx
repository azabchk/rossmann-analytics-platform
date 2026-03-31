import type { Metadata } from "next";

import ForecastView from "@/features/forecasts/forecast-view";

export const metadata: Metadata = {
  title: "Forecasts - Sales Forecasting Platform",
  description: "View published sales forecasts for accessible stores",
};

export default function ForecastsPage() {
  return <ForecastView />;
}
