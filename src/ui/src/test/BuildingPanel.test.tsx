import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BuildingPanel } from "@/components/explore/BuildingPanel";
import { api } from "@/api/client";
import type { BuildingDetail } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    getBuilding: vi.fn(),
  },
}));

const BUILDING: BuildingDetail = {
  building_id: "IS.355",
  address: "123 Test Street",
  neighborhood: "Cole",
  dataset: "data2",
  attributes: {
    architectural_style: "Bungalow",
    stories: "1",
  },
  images: [
    {
      filename: "test_image.jpg",
      original_url: "/images/data2/Cole/test_image.jpg",
      crop_url: "/crops/data2/Cole/test_image_crop.jpg",
    },
  ],
};

describe("BuildingPanel", () => {
  beforeEach(() => {
    vi.mocked(api.getBuilding).mockResolvedValue(BUILDING);
  });

  it("shows image skeletons while original and crop images are pending", async () => {
    render(<BuildingPanel dataset="data2" buildingId="IS.355" />);

    await screen.findByText("test_image.jpg");
    expect(screen.getByTestId("image-loading-original")).toBeInTheDocument();
    expect(screen.getByTestId("image-loading-crop")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "original" })).toHaveAttribute("src", BUILDING.images[0].original_url);
    expect(screen.getByRole("img", { name: "crop" })).toHaveAttribute("src", BUILDING.images[0].crop_url);
  });

  it("shows an inline error when an image fails to load", async () => {
    render(<BuildingPanel dataset="data2" buildingId="IS.355" />);

    await screen.findByText("test_image.jpg");
    fireEvent.error(screen.getByRole("img", { name: "crop" }));

    expect(screen.getByText("Image failed to load")).toBeInTheDocument();
    expect(screen.queryByTestId("image-loading-crop")).not.toBeInTheDocument();
  });
});