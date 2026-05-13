import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ImagePanel } from "@/components/explore/ImagePanel";
import type { BuildingImage } from "@/types";

const WITH_CROP: BuildingImage = {
  filename: "test_image.jpg",
  original_url: "/images/data2/Cole/test_image.jpg",
  crop_url: "/crops/data2/Cole/test_image_crop.jpg",
};

const WITHOUT_CROP: BuildingImage = {
  filename: "no_crop.jpg",
  original_url: "/images/data2/Cole/no_crop.jpg",
  crop_url: null,
};

describe("ImagePanel", () => {
  it("renders original and cropped images when crop is available", () => {
    render(<ImagePanel image={WITH_CROP} buildingId="IS.355" />);
    expect(screen.getByText("ORIGINAL")).toBeInTheDocument();
    expect(screen.getByText("CROPPED")).toBeInTheDocument();
    const imgs = screen.getAllByRole("img");
    expect(imgs).toHaveLength(2);
    expect(imgs[0]).toHaveAttribute("src", WITH_CROP.original_url);
    expect(imgs[1]).toHaveAttribute("src", WITH_CROP.crop_url);
  });

  it("shows 'No crop available' message when crop_url is null", () => {
    render(<ImagePanel image={WITHOUT_CROP} buildingId="IS.356" />);
    expect(screen.getByText(/no crop available/i)).toBeInTheDocument();
    const imgs = screen.getAllByRole("img");
    expect(imgs).toHaveLength(1);
  });

  it("renders the filename", () => {
    render(<ImagePanel image={WITH_CROP} buildingId="IS.355" />);
    expect(screen.getByText("test_image.jpg")).toBeInTheDocument();
  });
});
