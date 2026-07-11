import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { InferenceSidebar } from "@/components/inference/InferenceSidebar";
import type { CheckpointInfo } from "@/types";

const checkpoint: CheckpointInfo = {
  id: "run",
  short_name: "Best Phase 3",
  checkpoint_path: "outputs/combined/best_model_phase3.pth",
  backbone: "efficientnet_b5",
  phase: 3,
  best_overall_acc: 72.4,
  dataset_version: "combined",
  timestamp: "2026-07-10",
  run_name: "run",
  input_type: "paired",
  paired_views: true,
  paired_fusion_mode: "task_gated_residual",
  lr: 1e-4,
  backbone_lr_scale: 0.2,
  scheduler: "plateau",
  freeze_phase1_heads: false,
};

const baseProps = {
  checkpoints: [checkpoint],
  loadingCkpts: false,
  selectedCkpt: checkpoint.checkpoint_path,
  onSelectCkpt: vi.fn(),
  phaseFilter: new Set([2, 3]),
  onTogglePhase: vi.fn(),
  files: [],
  previews: [],
  onAddFiles: vi.fn(),
  onRemoveFile: vi.fn(),
  onClearFiles: vi.fn(),
  running: false,
  onRun: vi.fn(),
  medalMap: {},
};

describe("InferenceSidebar", () => {
  it("hides model and phase controls for anonymous users", () => {
    render(<InferenceSidebar {...baseProps} anonymous />);

    expect(screen.queryByLabelText("Model checkpoint")).not.toBeInTheDocument();
    expect(screen.queryByText("Phase 1")).not.toBeInTheDocument();
    expect(screen.getByText(/drop images here/i)).toBeInTheDocument();
  });
});