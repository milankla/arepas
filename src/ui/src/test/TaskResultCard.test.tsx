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

describe("TaskResultCard", () => {
  it("hides confidence chip and top choices in compact mode", () => {
    render(<TaskResultCard result={result} compact />);

    expect(screen.getByText("Gabled")).toBeInTheDocument();
    expect(screen.queryByText("81.2%")).not.toBeInTheDocument();
    expect(screen.queryByText("Hipped")).not.toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });
});