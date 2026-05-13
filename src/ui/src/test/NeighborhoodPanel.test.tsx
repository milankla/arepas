import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NeighborhoodPanel } from "@/components/explore/NeighborhoodPanel";
import type { NeighborhoodStats } from "@/types";

const STATS: NeighborhoodStats = {
  neighborhood: "Cole",
  building_count: 42,
  image_count: 150,
  attribute_frequencies: [
    {
      attribute: "primary_cladding",
      counts: { Brick: 30, Stucco: 8, "Siding - Vinyl": 4 },
    },
    {
      attribute: "stories",
      counts: { "1": 20, "1-1/2": 15, "2": 7 },
    },
  ],
};

describe("NeighborhoodPanel", () => {
  it("renders the neighborhood name", () => {
    render(<NeighborhoodPanel stats={STATS} />);
    expect(screen.getByText("Cole")).toBeInTheDocument();
  });

  it("renders building and image count chips", () => {
    render(<NeighborhoodPanel stats={STATS} />);
    expect(screen.getByText("42 buildings")).toBeInTheDocument();
    expect(screen.getByText("150 images")).toBeInTheDocument();
  });

  it("renders a chart section for each attribute", () => {
    render(<NeighborhoodPanel stats={STATS} />);
    expect(screen.getByText("Primary Cladding")).toBeInTheDocument();
    expect(screen.getByText("Stories")).toBeInTheDocument();
  });
});
