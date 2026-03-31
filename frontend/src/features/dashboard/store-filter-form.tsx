/**
 * Store Filter Form component.
 *
 * Provides UI for selecting stores and filtering by date range.
 * All validation and business logic is handled by the backend.
 */

import type { ChangeEvent, ReactNode } from "react";

import type { Store } from "@/lib/api/stores";

export interface StoreFilterFormProps {
  stores: Store[];
  selectedStoreId: number | null;
  startDate: string;
  endDate: string;
  onStoreSelect: (storeId: number | null) => void;
  onDateChange: (startDate: string, endDate: string) => void;
}

export default function StoreFilterForm({
  stores,
  selectedStoreId,
  startDate,
  endDate,
  onStoreSelect,
  onDateChange,
}: StoreFilterFormProps): ReactNode {
  function handleStoreChange(e: ChangeEvent<HTMLSelectElement>): void {
    const value = e.target.value;
    onStoreSelect(value ? Number(value) : null);
  }

  function handleStartDateChange(e: ChangeEvent<HTMLInputElement>): void {
    onDateChange(e.target.value, endDate);
  }

  function handleEndDateChange(e: ChangeEvent<HTMLInputElement>): void {
    onDateChange(startDate, e.target.value);
  }

  function handleQuickDateRange(days: number): void {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    onDateChange(start.toISOString().split("T")[0], end.toISOString().split("T")[0]);
  }

  return (
    <div className="store-filter-form">
      <div className="filter-section">
        <label htmlFor="store-select">Store</label>
        <select
          id="store-select"
          value={selectedStoreId ?? ""}
          onChange={handleStoreChange}
          disabled={stores.length === 0}
        >
          <option value="">Select a store...</option>
          {stores.map((store) => (
            <option key={store.store_id} value={store.store_id}>
              Store {store.store_id} - Type {store.store_type} -{" "}
              {store.assortment.toUpperCase()} assortment
            </option>
          ))}
        </select>
      </div>

      <div className="filter-section">
        <label htmlFor="start-date">Start Date</label>
        <input
          id="start-date"
          type="date"
          value={startDate}
          onChange={handleStartDateChange}
          max={endDate}
        />
      </div>

      <div className="filter-section">
        <label htmlFor="end-date">End Date</label>
        <input
          id="end-date"
          type="date"
          value={endDate}
          onChange={handleEndDateChange}
          min={startDate}
        />
      </div>

      <div className="quick-filters">
        <button
          type="button"
          onClick={() => handleQuickDateRange(7)}
          className="quick-filter-btn"
        >
          Last 7 days
        </button>
        <button
          type="button"
          onClick={() => handleQuickDateRange(30)}
          className="quick-filter-btn"
        >
          Last 30 days
        </button>
        <button
          type="button"
          onClick={() => handleQuickDateRange(90)}
          className="quick-filter-btn"
        >
          Last 90 days
        </button>
        <button
          type="button"
          onClick={() => handleQuickDateRange(365)}
          className="quick-filter-btn"
        >
          Last year
        </button>
      </div>
    </div>
  );
}
