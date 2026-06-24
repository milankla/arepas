import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Chip,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import { AppShell } from "@/components/layout/AppShell";
import { RunSelector } from "@/components/training/RunSelector";
import {
  AccuracyChart,
  LossChart,
  TaskMetricCharts,
  buildRunLabels,
  type RunHistoryMap,
} from "@/components/training/TrainingCharts";
import { RunCompareTable } from "@/components/training/RunCompareTable";
import { RunNotes } from "@/components/training/RunNotes";
import { api } from "@/api/client";
import { useDataset } from "@/context/DatasetContext";
import type { EpochRecord, RunInfo } from "@/types";

const PALETTE = [
  "#2196f3", "#f44336", "#4caf50", "#ff9800",
  "#9c27b0", "#00bcd4", "#795548", "#607d8b",
];

export default function TrainingEvaluationPage() {
  const { activeDataset } = useDataset();
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [histories, setHistories] = useState<Record<string, EpochRecord[]>>({});
  const [tab, setTab] = useState(0);

  // Filter runs by active dataset
  const visibleRuns = useMemo(
    () => runs.filter((r) => !activeDataset || r.dataset_version === activeDataset),
    [runs, activeDataset]
  );

  // Reset selection when the active dataset changes
  useEffect(() => {
    setSelectedIds(new Set());
  }, [activeDataset]);

  // Auto-select the most recent visible run when nothing in the current visible set is selected
  useEffect(() => {
    if (visibleRuns.length === 0) return;
    setSelectedIds((prev) => {
      const stillValid = visibleRuns.some((r) => prev.has(r.run_id));
      if (stillValid) return prev;
      const latest = [...visibleRuns].sort((a, b) => b.timestamp.localeCompare(a.timestamp))[0];
      return new Set([latest.run_id]);
    });
  }, [visibleRuns]);

  // Load run list on mount, then poll every 30 s for new/updated runs
  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .listRuns()
        .then((data) => { if (!cancelled) setRuns(data); })
        .finally(() => { if (!cancelled) setLoadingRuns(false); });
    load();
    const timer = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  // Fetch history for newly selected runs; re-fetch selected runs every 30 s
  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      for (const runId of selectedIds) {
        api.getRunHistory(runId).then((h) => {
          if (!cancelled) setHistories((prev) => ({ ...prev, [runId]: h }));
        });
      }
    };
    refresh();
    const timer = setInterval(refresh, 30_000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [selectedIds]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleRun = (runId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) {
        next.delete(runId);
      } else {
        next.add(runId);
      }
      return next;
    });
  };

  const selectedRuns = useMemo(
    () => visibleRuns.filter((r) => selectedIds.has(r.run_id)),
    [visibleRuns, selectedIds]
  );

  const selectedHistories: RunHistoryMap = useMemo(() => {
    const result: RunHistoryMap = {};
    for (const runId of selectedIds) {
      if (histories[runId]) result[runId] = histories[runId];
    }
    return result;
  }, [selectedIds, histories]);

  // Version-based labels: resnet50_v1, resnet50_v2_lr2e-4, …
  const runLabels = useMemo(() => buildRunLabels(visibleRuns), [visibleRuns]);

  // Shared X-axis ceiling: max epochs_completed across all selected runs (min 30)
  const epochMax = useMemo(
    () => Math.max(30, ...selectedRuns.map((r) => r.epochs_completed)),
    [selectedRuns]
  );

  const sidebar = (
    <RunSelector
      runs={visibleRuns}
      loading={loadingRuns}
      selectedIds={selectedIds}
      onToggle={toggleRun}
      runLabels={runLabels}
    />
  );

  const detail = (
    <Box>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
        Training Evaluation
      </Typography>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Compare" />
        <Tab label="Loss curves" />
        <Tab label="Accuracy" />
        <Tab label="Per-task" />
      </Tabs>

      {/* ── Compare tab ── */}
      {tab === 0 && (
        <Box>
          <RunCompareTable runs={selectedRuns} histories={selectedHistories} runLabels={runLabels} />
        </Box>
      )}

      {/* ── Loss curves tab ── */}
      {tab === 1 && (
        <Box>
          {selectedRuns.length === 0 ? (
            <Typography color="text.secondary">Select at least one run.</Typography>
          ) : (
            selectedRuns.map((run, i) =>
              selectedHistories[run.run_id] ? (
                <LossChart
                  key={run.run_id}
                  runId={run.run_id}
                  history={selectedHistories[run.run_id]}
                  color={PALETTE[i % PALETTE.length]}
                  label={runLabels[run.run_id]}
                  epochMax={epochMax}
                />
              ) : null
            )
          )}
        </Box>
      )}

      {/* ── Overall accuracy tab ── */}
      {tab === 2 && (
        <Box>
          {Object.keys(selectedHistories).length === 0 ? (
            <Typography color="text.secondary">Select at least one run.</Typography>
          ) : (
            <AccuracyChart histories={selectedHistories} runLabels={runLabels} epochMax={epochMax} />
          )}
        </Box>
      )}

      {/* ── Per-task tab ── */}
      {tab === 3 && (
        <Box>
          {Object.keys(selectedHistories).length === 0 ? (
            <Typography color="text.secondary">Select at least one run.</Typography>
          ) : (
            <TaskMetricCharts histories={selectedHistories} runLabels={runLabels} epochMax={epochMax} />
          )}
        </Box>
      )}

      {/* ── Model params — shown when exactly one run is selected ── */}
      {selectedRuns.length === 1 && (
        <Box sx={{ mt: 2, display: "flex", gap: 0.5, flexWrap: "wrap" }}>
          {[
            selectedRuns[0].backbone,
            `ph${selectedRuns[0].phase}`,
            `ep ${selectedRuns[0].epochs_completed}`,
            `acc ${(selectedRuns[0].best_overall_acc * 100).toFixed(1)}%`,
            `lr ${selectedRuns[0].lr.toExponential(0)}`,
            `bs ${selectedRuns[0].batch_size}`,
            `wd ${selectedRuns[0].weight_decay}`,
            selectedRuns[0].input_type,
            selectedRuns[0].paired_fusion_mode,
          ].map((p) => (
            p ? <Chip key={p} label={p} size="small" variant="outlined" sx={{ fontSize: 10, height: 18 }} /> : null
          ))}
        </Box>
      )}

      {/* ── Run notes — shown when exactly one run is selected and it has notes ── */}
      {selectedRuns.length === 1 && selectedRuns[0].notes && (
        <RunNotes runId={selectedRuns[0].run_id} notes={selectedRuns[0].notes} />
      )}
    </Box>
  );

  return <AppShell sidebar={sidebar} detail={detail} />;
}
