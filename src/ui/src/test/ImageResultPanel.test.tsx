import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ImageResultPanel } from "@/components/inference/ImageResultPanel";
import type { ImageResult } from "@/types";

describe("ImageResultPanel", () => {
  it("shows a friendly no-building message instead of task cards", () => {
    const result: ImageResult = {
      filename: "street.jpg",
      tasks: [],
      auto_cropped: false,
      cropped_image_b64: null,
      building_detected: false,
      message: "No building detected",
    };

    render(
      <ImageResultPanel
        result={result}
        previewUrl="blob:street"
        label="street.jpg"
        onImageClick={vi.fn()}
      />
    );

    expect(screen.getByText("No building detected")).toBeInTheDocument();
    expect(screen.getByText("Try a clearer exterior building photo.")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Original" })).toHaveAttribute("src", "blob:street");
  });
});