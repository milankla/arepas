/**
 * Comparison table of best-epoch metrics across selected runs.
 * Uses MUI Table (not DataGrid — no extra license needed).
 */
import {
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMemo, useState } from "react";
import type { EpochRecord, RunInfo } from "@/types";

export type RunHistoryMap = Record<string, EpochRecord[]>;

interface RunCompareTableProps {
  runs: RunInfo[];
  histories: RunHistoryMap;
  runLabels?: Record<string, string>;
}

interface RowData {
  runId: string;
  backbone: string;
  phase: number;
  epochs: number;
  lr: number;
  wd: number;
  batchSize: number;
  bestAcc: number;
  bestLoss: number;
  bestEpochAcc: number;
  bestEpochLoss: number;
  // per-task at best-acc epoch
  stories_acc: number;
  stories_f1: number;
  roof_acc: number;
  roof_f1: number;
  cladding_acc: number;
  cladding_f1: number;
  chimney_acc: number;
  chimney_f1: number;
  setting_exact: number;
  setting_f1: number;
}

function pct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function taskMetric(metrics: Record<string, unknown>, task: string, key: string): number {
  const m = metrics[task];
  if (!m || typeof m !== "object") return 0;
  return ((m as Record<string, number>)[key] ?? 0);
}

function buildRows(runs: RunInfo[], histories: RunHistoryMap): RowData[] {
  return runs
    .filter((r) => histories[r.run_id]?.length > 0)
    .map((r) => {
      const h = histories[r.run_id];
      const bestAccEpoch = h.reduce((best, e) =>
        e.overall_accuracy > best.overall_accuracy ? e : best
      );
      const bestLossEpoch = h.reduce((best, e) =>
        e.val_loss_total < best.val_loss_total ? e : best
      );
      const m = bestAccEpoch.val_metrics;
      return {
        runId: r.run_id,
        backbone: r.backbone,
        phase: r.phase,
        epochs: r.epochs_completed,
        lr: r.lr,
        wd: r.weight_decay,
        batchSize: r.batch_size,
        bestAcc: bestAccEpoch.overall_accuracy,
        bestLoss: bestLossEpoch.val_loss_total,
        bestEpochAcc: bestAccEpoch.epoch,
        bestEpochLoss: bestLossEpoch.epoch,
        stories_acc: taskMetric(m, "stories", "acc"),
        stories_f1: taskMetric(m, "stories", "f1"),
        roof_acc: taskMetric(m, "roof_type", "acc"),
        roof_f1: taskMetric(m, "roof_type", "f1"),
        cladding_acc: taskMetric(m, "primary_cladding", "acc"),
        cladding_f1: taskMetric(m, "primary_cladding", "f1"),
        chimney_acc: taskMetric(m, "chimney_present", "acc"),
        chimney_f1: taskMetric(m, "chimney_present", "f1"),
        setting_exact: taskMetric(m, "setting", "exact"),
        setting_f1: taskMetric(m, "setting", "f1"),
      };
    });
}

type SortKey = keyof RowData;

// Find the best value per column to highlight
function bestPerCol(rows: RowData[]): Partial<Record<SortKey, number>> {
  if (rows.length === 0) return {};
  const higherIsBetter: SortKey[] = [
    "bestAcc", "stories_acc", "stories_f1", "roof_acc", "roof_f1",
    "cladding_acc", "cladding_f1", "chimney_acc", "chimney_f1",
    "setting_exact", "setting_f1",
  ];
  const lowerIsBetter: SortKey[] = ["bestLoss"];
  const result: Partial<Record<SortKey, number>> = {};
  for (const k of higherIsBetter) {
    result[k] = Math.max(...rows.map((r) => r[k] as number));
  }
  for (const k of lowerIsBetter) {
    result[k] = Math.min(...rows.map((r) => r[k] as number));
  }
  return result;
}

export function RunCompareTable({ runs, histories, runLabels }: RunCompareTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("bestAcc");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const rows = useMemo(() => buildRows(runs, histories), [runs, histories]);
  const best = useMemo(() => bestPerCol(rows), [rows]);

  const sorted = useMemo(() => {
    return [...rows].sort((a, b) => {
      const av = a[sortKey] as number | string;
      const bv = b[sortKey] as number | string;
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [rows, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  if (rows.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Select runs in the sidebar to compare.
      </Typography>
    );
  }

  const phases = new Set(rows.map((r) => r.phase));
  const crossPhase = phases.size > 1;

  function SH({ label, k, tip }: { label: string; k: SortKey; tip?: string }) {
    const cell = (
      <TableCell sx={{ whiteSpace: "nowrap", fontWeight: 600, fontSize: 12 }}>
        <TableSortLabel
          active={sortKey === k}
          direction={sortKey === k ? sortDir : "desc"}
          onClick={() => handleSort(k)}
        >
          {label}
        </TableSortLabel>
      </TableCell>
    );
    return tip ? <Tooltip title={tip}>{cell}</Tooltip> : cell;
  }

  function PC({ row, k }: { row: RowData; k: SortKey }) {
    const v = row[k] as number;
    const isBest = best[k] !== undefined && v === best[k] && rows.length > 1;
    return (
      <TableCell
        sx={{
          fontSize: 12,
          fontWeight: isBest ? 700 : 400,
          color: isBest ? "success.main" : "text.primary",
        }}
      >
        {pct(v)}
      </TableCell>
    );
  }

  return (
    <>
      {crossPhase && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Comparing runs from different phases (phase {Array.from(phases).sort().join(" vs ")}). Overall
          accuracy is not directly comparable — phase 2 trains 7 tasks vs phase 1’s 5. Per-task metrics
          for shared tasks (stories, roof, cladding, chimney, setting) remain valid.
        </Alert>
      )}
      <TableContainer component={Paper} variant="outlined">
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow sx={{ "& th": { bgcolor: "background.default" } }}>
            <TableCell sx={{ fontWeight: 600, fontSize: 12, minWidth: 180 }}>Run</TableCell>
            <SH label="Phase" k="phase" />
            <SH label="Ep" k="epochs" tip="Epochs completed" />
            <SH label="LR" k="lr" />
            <SH label="WD" k="wd" tip="Weight decay" />
            <SH label="BS" k="batchSize" tip="Batch size" />
            <SH label="Best Acc" k="bestAcc" />
            <SH label="@ep" k="bestEpochAcc" tip="Epoch of best accuracy" />
            <SH label="Best Loss" k="bestLoss" />
            <SH label="@ep" k="bestEpochLoss" tip="Epoch of best val loss" />
            <SH label="Stories acc" k="stories_acc" />
            <SH label="Stories F1" k="stories_f1" />
            <SH label="Roof acc" k="roof_acc" />
            <SH label="Roof F1" k="roof_f1" />
            <SH label="Cladding acc" k="cladding_acc" />
            <SH label="Cladding F1" k="cladding_f1" />
            <SH label="Chimney acc" k="chimney_acc" />
            <SH label="Chimney F1" k="chimney_f1" />
            <SH label="Setting exact" k="setting_exact" />
            <SH label="Setting F1" k="setting_f1" />
          </TableRow>
        </TableHead>
        <TableBody>
          {sorted.map((row) => (
            <TableRow key={row.runId} hover>
              <TableCell sx={{ fontSize: 11, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                <Tooltip title={row.runId}>
                  <span>{runLabels?.[row.runId] ?? row.runId.replace(/^[^/]+\//, "")}</span>
                </Tooltip>
              </TableCell>
              <TableCell sx={{ fontSize: 12 }}>{row.phase}</TableCell>
              <TableCell sx={{ fontSize: 12 }}>{Math.round(row.epochs)}</TableCell>
              <TableCell sx={{ fontSize: 12 }}>{row.lr.toExponential(1)}</TableCell>
              <TableCell sx={{ fontSize: 12 }}>{row.wd}</TableCell>
              <TableCell sx={{ fontSize: 12 }}>{row.batchSize}</TableCell>
              <PC row={row} k="bestAcc" />
              <TableCell sx={{ fontSize: 12 }}>{Math.round(row.bestEpochAcc)}</TableCell>
              <TableCell sx={{ fontSize: 12 }}>{row.bestLoss.toFixed(4)}</TableCell>
              <TableCell sx={{ fontSize: 12 }}>{Math.round(row.bestEpochLoss)}</TableCell>
              <PC row={row} k="stories_acc" />
              <PC row={row} k="stories_f1" />
              <PC row={row} k="roof_acc" />
              <PC row={row} k="roof_f1" />
              <PC row={row} k="cladding_acc" />
              <PC row={row} k="cladding_f1" />
              <PC row={row} k="chimney_acc" />
              <PC row={row} k="chimney_f1" />
              <PC row={row} k="setting_exact" />
              <PC row={row} k="setting_f1" />
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
    </>
  );
}
