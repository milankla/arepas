import { describe, expect, it } from "vitest";
import { defaultCheckpoint } from "@/pages/InferencePage";
import type { CheckpointInfo } from "@/types";

function ckpt(overrides: Partial<CheckpointInfo>): CheckpointInfo {
  return {
    id: overrides.id ?? "run",
    short_name: overrides.short_name ?? "run",
    checkpoint_path: overrides.checkpoint_path ?? "outputs/run/best_model_phase2.pth",
    backbone: "efficientnet_b5",
    phase: overrides.phase ?? 2,
    best_overall_acc: overrides.best_overall_acc ?? 70,
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
}

describe("defaultCheckpoint", () => {
  it("chooses the best Phase 3 checkpoint over newer or stronger non-Phase 3 runs", () => {
    const selected = defaultCheckpoint([
      ckpt({ phase: 2, best_overall_acc: 90, checkpoint_path: "outputs/phase2.pth" }),
      ckpt({ phase: 3, best_overall_acc: 72.4, checkpoint_path: "outputs/phase3-good.pth" }),
      ckpt({ phase: 3, best_overall_acc: 65, checkpoint_path: "outputs/phase3-low.pth" }),
    ]);

    expect(selected?.checkpoint_path).toBe("outputs/phase3-good.pth");
  });

  it("falls back to the best available checkpoint if Phase 3 is absent", () => {
    const selected = defaultCheckpoint([
      ckpt({ phase: 1, best_overall_acc: 60, checkpoint_path: "outputs/phase1.pth" }),
      ckpt({ phase: 2, best_overall_acc: 74, checkpoint_path: "outputs/phase2.pth" }),
    ]);

    expect(selected?.checkpoint_path).toBe("outputs/phase2.pth");
  });
});