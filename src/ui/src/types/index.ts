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
  dataset: string;
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
  neighborhood: string;
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

// ---------------------------------------------------------------------------
// Training runs
// ---------------------------------------------------------------------------

export interface RunNotes {
  summary: string;
  learnings: string[];
  next_steps: string[];
}

export interface RunInfo {
  run_id: string;
  short_name: string;
  backbone: string;
  phase: number;
  epochs_completed: number;
  best_val_loss: number;
  best_overall_acc: number;
  batch_size: number;
  lr: number;
  weight_decay: number;
  dataset_version: string;
  timestamp: string;
  run_name: string;
  input_type: "crop" | "full" | "paired";
  paired_views: boolean;
  paired_fusion_mode?: string | null;
  notes?: RunNotes | null;
}

export interface EpochRecord {
  epoch: number;
  train_loss_total: number;
  val_loss_total: number;
  overall_accuracy: number;
  train_losses: Record<string, number>;
  val_losses: Record<string, number>;
  val_metrics: Record<string, Record<string, number> | number>;
}

// ---------------------------------------------------------------------------
// Inference
// ---------------------------------------------------------------------------

export interface CheckpointInfo {
  id: string;
  short_name: string;
  checkpoint_path: string;
  backbone: string;
  phase: number;
  best_overall_acc: number;
  dataset_version: string;
  timestamp: string;
  run_name: string;
  input_type: "crop" | "full" | "paired";
  paired_views: boolean;
  paired_fusion_mode?: string | null;
  lr: number;
  backbone_lr_scale: number | null;
  scheduler: string;
  freeze_phase1_heads: boolean;
}

export interface ClassConfidence {
  label: string;
  confidence: number; // 0–100
}

export interface TaskResult {
  task: string;
  predicted: string;
  confidence: number; // 0–100
  top3: ClassConfidence[];  is_multi_label?: boolean;}

export interface ImageResult {
  filename: string;
  tasks: TaskResult[];
  auto_cropped: boolean;
  cropped_image_b64?: string | null;
  building_detected?: boolean | null;
  message?: string | null;
}

export interface InferenceResponse {
  per_image: ImageResult[];
  aggregated: TaskResult[] | null;
  auto_cropped: boolean;
}
