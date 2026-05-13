// ---------------------------------------------------------------------------
// Shared TypeScript types mirroring the FastAPI response models
// ---------------------------------------------------------------------------

export interface DatasetInfo {
  id: string;
  label: string;
  building_count: number;
  image_count: number;
  neighborhoods: string[];
}

export interface AttributeFrequency {
  attribute: string;
  counts: Record<string, number>;
}

export interface NeighborhoodStats {
  neighborhood: string;
  building_count: number;
  image_count: number;
  attribute_frequencies: AttributeFrequency[];
}

export interface BuildingSummary {
  building_id: string;
  address: string | null;
  neighborhood: string;
  image_count: number;
  thumbnail_url: string;
}

export interface BuildingImage {
  filename: string;
  original_url: string;
  crop_url: string | null;
}

export interface BuildingDetail {
  building_id: string;
  address: string | null;
  neighborhood: string;
  attributes: Record<string, string | null>;
  images: BuildingImage[];
}

// ---------------------------------------------------------------------------
// UI selection state
// ---------------------------------------------------------------------------
export type SelectionType = "neighborhood" | "building" | "image";

export interface NeighborhoodSelection {
  type: "neighborhood";
  dataset: string;
  neighborhood: string;
}

export interface BuildingSelection {
  type: "building";
  dataset: string;
  building_id: string;
}

export interface ImageSelection {
  type: "image";
  dataset: string;
  building_id: string;
  image: BuildingImage;
}

export type TreeSelection =
  | NeighborhoodSelection
  | BuildingSelection
  | ImageSelection;
