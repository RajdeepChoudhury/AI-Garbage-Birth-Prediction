import { describe, expect, it } from "vitest";
import { filterForecasts, urgencyColor, urgencyLabel } from "./utils";
import type { Forecast, Risk } from "./types";

const make = (ward: number, risk: Risk, urgency: number): Forecast => ({
  id: ward, ward, latitude: 0, longitude: 0, forecast_date: "2026-10-02", predicted_volume: 1,
  risk_level: risk, hotspot_probability: 0.1, urgency_score: urgency, confidence: 0.5,
  recommended_cleaning_time: "Within 24 hours", predicted_overflow_date: null, top_factors: null, created_at: "",
});

describe("urgency scale", () => {
  it("maps band edges to the five spec colours", () => {
    expect(urgencyColor(0)).toBe("#22c55e");
    expect(urgencyColor(20)).toBe("#eab308");
    expect(urgencyColor(40)).toBe("#f97316");
    expect(urgencyColor(60)).toBe("#dc2626");
    expect(urgencyColor(80)).toBe("#7f1d1d");
    expect(urgencyColor(100)).toBe("#7f1d1d");
  });
  it("labels bands", () => {
    expect(urgencyLabel(10)).toBe("Very low");
    expect(urgencyLabel(95)).toBe("Severe");
  });
});

describe("filterForecasts", () => {
  const data = [make(17, "High", 70), make(2, "Low", 10), make(170, "Critical", 90), make(5, "High", 65)];
  it("sorts by urgency, highest first", () => {
    expect(filterForecasts(data, "", "All").map((f) => f.ward)).toEqual([170, 17, 5, 2]);
  });
  it("filters by risk level", () => {
    expect(filterForecasts(data, "", "High").map((f) => f.ward)).toEqual([17, 5]);
  });
  it("searches by ward number and accepts a ward prefix", () => {
    expect(filterForecasts(data, "17", "All").map((f) => f.ward)).toEqual([170, 17]);
    expect(filterForecasts(data, "Ward 5", "All").map((f) => f.ward)).toEqual([5]);
  });
  it("does not mutate its input", () => {
    const copy = [...data];
    filterForecasts(data, "", "All");
    expect(data).toEqual(copy);
  });
});
