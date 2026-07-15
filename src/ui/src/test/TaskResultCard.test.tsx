import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TaskResultCard } from "@/components/inference/TaskResultCard";
import type { TaskResult } from "@/types";

const result: TaskResult = {
  task: "roof_type",
  predicted: "Gabled",
  confidence: 81.2,
  top3: [
    { label: "Gabled", confidence: 81.2 },
    { label: "Hipped", confidence: 12.3 },
    { label: "Flat", confidence: 6.5 },
  ],
};

const multiLabelResult: TaskResult = {
  task: "landscape_features",
  predicted: "Street Trees",
  confidence: 78.5,
  top3: [
    { label: "Street Trees", confidence: 78.5 },
    { label: "Fence", confidence: 61.2 },
    { label: "Garage", confidence: 44.1 },
  ],
  is_multi_label: true,
};

describe("TaskResultCard", () => {
  it("hides confidence chip and top choices in compact mode for single-label", () => {
    render(<TaskResultCard result={result} compact />);

    expect(screen.getByText("Gabled")).toBeInTheDocument();
    expect(screen.queryByText("81.2%")).not.toBeInTheDocument();
    expect(screen.queryByText("Hipped")).not.toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows labels above 50% threshold dot-separated in compact mode for multi-label", () => {
    // Street Trees 78.5% and Fence 61.2% are above threshold; Garage 44.1% is not
    render(<TaskResultCard result={multiLabelResult} compact />);

    expect(screen.getByText("Street Trees · Fence")).toBeInTheDocument();
    expect(screen.queryByText("Garage")).not.toBeInTheDocument();
    expect(screen.queryByText("78.5%")).not.toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("falls back to top-1 label in compact mode when no multi-label exceeds threshold", () => {
    const lowConfResult: TaskResult = {
      ...multiLabelResult,
      top3: [
        { label: "Street Trees", confidence: 45.0 },
        { label: "Fence", confidence: 30.0 },
        { label: "Garage", confidence: 20.0 },
      ],
    };
    render(<TaskResultCard result={lowConfResult} compact />);

    expect(screen.getByText("Street Trees")).toBeInTheDocument();
  });

  it("shows predicted value and confidence chip in non-compact mode for multi-label", () => {
    render(<TaskResultCard result={multiLabelResult} compact={false} />);

    // predicted appears in the header row (also appears in top3 caption)
    expect(screen.getAllByText("Street Trees").length).toBeGreaterThanOrEqual(1);
    // confidence chip span
    expect(screen.getAllByText("78.5%").length).toBeGreaterThanOrEqual(1);
    // top3 alternatives visible
    expect(screen.getByText("Fence")).toBeInTheDocument();
  });
});