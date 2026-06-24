import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Box,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import type { EpochRecord, RunInfo } from "@/types";

// Stable palette — first 8 colours
const PALETTE = [
  "#2196f3",
  "#f44336",
  "#4caf50",
  "#ff9800",
  "#9c27b0",
  "#00bcd4",
  "#795548",
  "#607d8b",
];

export type RunHistoryMap = Record<string, EpochRecord[]>;
type ChartRow = Record<string, number | null | undefined>;

// All tasks that can appear in per-task metric charts
type TaskType = "single-label" | "multi-label";

interface TaskDefinition {
  key: string;
  label: string;
  type: TaskType;
  primaryMetricLabel: string;
}

interface TaskPhaseGroup {
  phase: number;
  title: string;
  tasks: TaskDefinition[];
}

const TASK_PHASE_GROUPS: TaskPhaseGroup[] = [
  {
    phase: 1,
    title: "Phase 1 - Easy visual features",
    tasks: [
      { key: "stories", label: "Stories", type: "single-label", primaryMetricLabel: "Accuracy" },
      { key: "roof_type", label: "Roof type", type: "single-label", primaryMetricLabel: "Accuracy" },
      { key: "primary_cladding", label: "Primary cladding", type: "single-label", primaryMetricLabel: "Accuracy" },
      { key: "chimney_present", label: "Chimney present", type: "single-label", primaryMetricLabel: "Accuracy" },
      { key: "setting", label: "Setting", type: "multi-label", primaryMetricLabel: "Exact match" },
      { key: "alteration_level", label: "Alteration level", type: "single-label", primaryMetricLabel: "Accuracy" },
    ],
  },
  {
    phase: 2,
    title: "Phase 2 - Architectural classification",
    tasks: [
      { key: "architectural_style", label: "Architectural style", type: "single-label", primaryMetricLabel: "Accuracy" },
      { key: "building_form", label: "Building form", type: "single-label", primaryMetricLabel: "Accuracy" },
    ],
  },
  {
    phase: 3,
    title: "Phase 3 - Fine-grained features",
    tasks: [
      { key: "wall_features", label: "Wall features", type: "multi-label", primaryMetricLabel: "Jaccard" },
      { key: "landscape_features", label: "Landscape features", type: "multi-label", primaryMetricLabel: "Jaccard" },
      { key: "window", label: "Window", type: "multi-label", primaryMetricLabel: "Jaccard" },
      { key: "entrance", label: "Entrance", type: "multi-label", primaryMetricLabel: "Jaccard" },
      { key: "associated_buildings", label: "Associated buildings", type: "multi-label", primaryMetricLabel: "Jaccard" },
      { key: "building_category", label: "Building category", type: "single-label", primaryMetricLabel: "Accuracy" },
      { key: "roof_materials", label: "Roof materials", type: "multi-label", primaryMetricLabel: "Jaccard" },
    ],
  },
];

const ALL_TASKS = TASK_PHASE_GROUPS.flatMap((group) => group.tasks.map((task) => task.key));

export function formatRunLabel(runId: string, runLabels?: Record<string, string>): string {
  return runLabels?.[runId] ?? runId.replace(/^[^/]+\//, "");
}

/**
 * Build version-based labels for a set of runs, grouped by backbone + phase:
 *   first run  → "{backbone}_v1_ph{N}"
 *   subsequent → "{backbone}_v{N}_{changed_params}_ph{N}"
 * Params compared vs the group's v1 baseline: lr, weight_decay, batch_size.
 */
export function buildRunLabels(runs: RunInfo[]): Record<string, string> {
  // Count how many distinct phases exist per short_name to detect ph1+ph2 pairs
  const namePhases: Record<string, Set<number>> = {};
  for (const run of runs) {
    (namePhases[run.short_name] ??= new Set()).add(run.phase);
  }
  const labels: Record<string, string> = {};
  for (const run of runs) {
    const multiPhase = (namePhases[run.short_name]?.size ?? 0) > 1;
    labels[run.run_id] = multiPhase
      ? `${run.short_name} · ph${run.phase}`
      : run.short_name;
  }
  return labels;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a per-epoch series for a single scalar field across multiple runs. */
function buildSeries(
  histories: RunHistoryMap,
  getVal: (e: EpochRecord) => number | null | undefined
): ChartRow[] {
  // Determine max epoch
  const maxEpoch = Math.max(
    ...Object.values(histories).map((h) => (h.length > 0 ? h[h.length - 1].epoch : 0))
  );
  const rows: ChartRow[] = [];
  for (let ep = 1; ep <= maxEpoch; ep++) {
    const row: ChartRow = { epoch: ep };
    for (const [runId, history] of Object.entries(histories)) {
      const rec = history.find((e) => e.epoch === ep);
      if (rec !== undefined) row[runId] = getVal(rec);
    }
    rows.push(row);
  }
  return rows;
}

function runLabel(runId: string, runLabels?: Record<string, string>) {
  return formatRunLabel(runId, runLabels);
}

// ---------------------------------------------------------------------------
// Shared chart-below table
// ---------------------------------------------------------------------------

interface ColDef {
  key: string;
  header: string;
  format?: (v: number) => string;
}

function ChartDataTable({
  data,
  columns,
}: {
  data: ChartRow[];
  columns: ColDef[];
}) {
  const rows = data.filter((row) =>
    columns.some((c) => c.key !== "epoch" && row[c.key] != null)
  );
  return (
    <TableContainer
      component={Paper}
      variant="outlined"
      sx={{ maxHeight: 320, overflowX: "auto", overflowY: "auto" }}
    >
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {columns.map((col) => (
              <TableCell
                key={col.key}
                sx={{ fontSize: 11, fontWeight: 600, whiteSpace: "nowrap", minWidth: 64 }}
              >
                {col.header}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={String(row.epoch)} hover>
              {columns.map((col) => {
                const val = row[col.key];
                return (
                  <TableCell key={col.key} sx={{ fontSize: 11, whiteSpace: "nowrap" }}>
                    {typeof val === "number"
                      ? col.format
                        ? col.format(val)
                        : val.toFixed(4)
                      : "—"}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

// ---------------------------------------------------------------------------
// Shared chart wrapper
// ---------------------------------------------------------------------------

interface ChartProps {
  title: string;
  data: ChartRow[];
  runIds: string[];
  runLabels?: Record<string, string>;
  yLabel?: string;
  yFormatter?: (v: number) => string;
  domain?: [number | "auto", number | "auto"];
  epochMax?: number;
  showTable?: boolean;
  height?: number;
}

function TrainingChart({
  title,
  data,
  runIds,
  runLabels,
  yLabel,
  yFormatter,
  domain,
  epochMax,
  showTable = true,
  height = 260,
}: ChartProps) {
  if (data.length === 0 || runIds.length === 0) return null;

  const tableCols: ColDef[] = [
    { key: "epoch", header: "Epoch", format: (v: number) => String(Math.round(v)) },
    ...runIds.map((id) => ({
      key: id,
      header: runLabel(id, runLabels),
      format: yFormatter,
    })),
  ];

  return (
    <Box sx={{ mb: 4, width: "100%", minWidth: 0 }}>
      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
        {title}
      </Typography>
      {/* Chart left, table right on md+; stacked on sm and below */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: showTable ? "row" : "column" },
          gap: 2,
          alignItems: "flex-start",
          width: "100%",
          minWidth: 0,
        }}
      >
        <Box sx={{ flex: showTable ? "1 1 60%" : "1 1 auto", minWidth: 0, width: "100%" }}>
          <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="epoch"
            label={{ value: "Epoch", position: "insideBottom", offset: -2, fontSize: 11 }}
            tick={{ fontSize: 11 }}
            domain={epochMax ? [1, epochMax] : ["auto", "auto"]}
            type="number"
            allowDataOverflow
          />
          <YAxis
            tickFormatter={yFormatter}
            label={
              yLabel
                ? { value: yLabel, angle: -90, position: "insideLeft", fontSize: 11 }
                : undefined
            }
            tick={{ fontSize: 11 }}
            domain={domain}
          />
          <Tooltip
            formatter={(val, name) => [
              typeof val === "number"
                ? yFormatter
                  ? yFormatter(val)
                  : val.toFixed(4)
                : String(val),
              runLabel(String(name), runLabels),
            ]}
            labelFormatter={(ep) => `Epoch ${ep}`}
          />
          <Legend
            formatter={(value) => runLabel(value, runLabels)}
            wrapperStyle={{ fontSize: 11 }}
          />
          {runIds.map((runId, i) => (
            <Line
              key={runId}
              type="monotone"
              dataKey={runId}
              stroke={PALETTE[i % PALETTE.length]}
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
        </Box>
        {showTable && (
          <Box sx={{ flex: "1 1 40%", minWidth: 0, width: { xs: "100%", md: "auto" } }}>
            <ChartDataTable data={data} columns={tableCols} />
          </Box>
        )}
      </Box>
    </Box>
  );
}

interface LossChartProps {
  runId: string;
  history: EpochRecord[];
  color: string;
  label?: string;
  epochMax?: number;
}

export function LossChart({ runId, history, color, label, epochMax }: LossChartProps) {
  const data = history.map((e) => ({
    epoch: e.epoch,
    train: e.train_loss_total,
    val: e.val_loss_total,
  }));
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="subtitle2" sx={{ mb: 0.5, fontWeight: 600 }}>
        Loss — {label ?? runLabel(runId)}
      </Typography>
      {/* Chart left, table right on md+; stacked on sm and below */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: 2,
          alignItems: "flex-start",
        }}
      >
        <Box sx={{ flex: "1 1 60%", minWidth: 0 }}>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data} margin={{ top: 4, right: 24, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis
                dataKey="epoch"
                tick={{ fontSize: 11 }}
                domain={epochMax ? [1, epochMax] : ["auto", "auto"]}
                type="number"
                allowDataOverflow
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip labelFormatter={(ep) => `Epoch ${ep}`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line
                type="monotone"
                dataKey="train"
                name="Train Loss"
                stroke={color}
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="val"
                name="Val Loss"
                stroke={color}
                dot={false}
                strokeWidth={2}
                strokeDasharray="5 3"
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
        <Box sx={{ flex: "1 1 40%", minWidth: 0, width: { xs: "100%", md: "auto" } }}>
          <ChartDataTable
            data={data}
            columns={[
              { key: "epoch", header: "Epoch", format: (v: number) => String(Math.round(v)) },
              { key: "train", header: "Train Loss" },
              { key: "val", header: "Val Loss" },
            ]}
          />
        </Box>
      </Box>
    </Box>
  );
}

// ---------------------------------------------------------------------------
// Overall accuracy across runs
// ---------------------------------------------------------------------------

export function AccuracyChart({ histories, runLabels, epochMax }: { histories: RunHistoryMap; runLabels?: Record<string, string>; epochMax?: number }) {
  const runIds = Object.keys(histories);
  const data = buildSeries(histories, (e) => e.overall_accuracy * 100);
  return (
    <TrainingChart
      title="Overall Accuracy (val)"
      data={data}
      runIds={runIds}
      runLabels={runLabels}
      yLabel="%"
      yFormatter={(v) => `${v.toFixed(1)}%`}
      domain={[60, 100]}
      epochMax={epochMax}
    />
  );
}

// ---------------------------------------------------------------------------
// Per-task metrics across runs
// ---------------------------------------------------------------------------

function hasTaskMetric(histories: RunHistoryMap, taskKey: string) {
  return Object.values(histories).some((history) =>
    history.some((e) => Boolean(e.val_metrics[taskKey]))
  );
}

function taskPrimaryMetricValue(metric: Record<string, number>, task: TaskDefinition) {
  if (task.type === "multi-label") return metric.jaccard ?? metric.exact ?? metric.acc ?? 0;
  return metric.acc ?? metric.exact ?? metric.jaccard ?? 0;
}

function typeCounts(tasks: TaskDefinition[]) {
  const counts = tasks.reduce(
    (acc, task) => ({ ...acc, [task.type]: acc[task.type] + 1 }),
    { "single-label": 0, "multi-label": 0 } satisfies Record<TaskType, number>
  );
  return Object.entries(counts).filter(([, count]) => count > 0);
}

export function TaskMetricCharts({ histories, runLabels, epochMax }: { histories: RunHistoryMap; runLabels?: Record<string, string>; epochMax?: number }) {
  const runIds = Object.keys(histories);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3, width: "100%", minWidth: 0 }}>
      {TASK_PHASE_GROUPS.map((group) => {
        const visibleTasks = group.tasks.filter((task) => hasTaskMetric(histories, task.key));
        if (visibleTasks.length === 0) return null;

        return (
          <Box key={group.phase} sx={{ width: "100%", minWidth: 0 }}>
            <Box sx={{ mb: 1.5, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                {group.title}
              </Typography>
              {typeCounts(visibleTasks).map(([type, count]) => (
                <Chip
                  key={type}
                  label={`${count} ${type}`}
                  size="small"
                  variant="outlined"
                  sx={{ height: 20, fontSize: 11 }}
                />
              ))}
            </Box>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {visibleTasks.map((task) => {
                const primaryData = buildSeries(histories, (e) => {
                  const metric = e.val_metrics[task.key];
                  if (!metric || typeof metric === "number") return null;
                  return taskPrimaryMetricValue(metric, task) * 100;
                });
                const f1Data = buildSeries(histories, (e) => {
                  const metric = e.val_metrics[task.key];
                  if (!metric || typeof metric === "number") return null;
                  return (metric.f1 ?? 0) * 100;
                });

                return (
                  <Paper key={task.key} variant="outlined" sx={{ p: 2, width: "100%", minWidth: 0 }}>
                    <Box sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        {task.label}
                      </Typography>
                      <Chip
                        label={task.type}
                        size="small"
                        variant="outlined"
                        sx={{ height: 18, fontSize: 10 }}
                      />
                    </Box>
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) minmax(0, 1fr)" },
                        gap: 2,
                        width: "100%",
                        minWidth: 0,
                      }}
                    >
                      <TrainingChart
                        title={`${task.primaryMetricLabel} (val)`}
                        data={primaryData}
                        runIds={runIds}
                        runLabels={runLabels}
                        yFormatter={(v) => `${v.toFixed(1)}%`}
                        domain={[0, 100]}
                        epochMax={epochMax}
                        showTable={false}
                        height={220}
                      />
                      <TrainingChart
                        title="Macro F1 (val)"
                        data={f1Data}
                        runIds={runIds}
                        runLabels={runLabels}
                        yFormatter={(v) => `${v.toFixed(1)}%`}
                        domain={[0, 100]}
                        epochMax={epochMax}
                        showTable={false}
                        height={220}
                      />
                    </Box>
                  </Paper>
                );
              })}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}

// ---------------------------------------------------------------------------
// Per-task accuracy across runs
// ---------------------------------------------------------------------------

export function TaskAccuracyCharts({ histories, runLabels, epochMax }: { histories: RunHistoryMap; runLabels?: Record<string, string>; epochMax?: number }) {
  const runIds = Object.keys(histories);
  // Determine which tasks are present
  const tasks = new Set<string>();
  for (const history of Object.values(histories)) {
    for (const e of history) {
      for (const task of ALL_TASKS) {
        if (e.val_metrics[task]) tasks.add(task);
      }
    }
  }

  return (
    <>
      {Array.from(tasks).map((task) => {
        const data = buildSeries(histories, (e) => {
          const m = e.val_metrics[task];
          if (!m || typeof m === "number") return 0;
          return (m.acc ?? m.exact ?? 0) * 100;
        });
        return (
          <TrainingChart
            key={task}
            title={`${task} — accuracy (val)`}
            data={data}
            runIds={runIds}
            runLabels={runLabels}
            yFormatter={(v) => `${v.toFixed(1)}%`}
            domain={[60, 100]}
            epochMax={epochMax}
          />
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Per-task F1 across runs
// ---------------------------------------------------------------------------

export function TaskF1Charts({ histories, runLabels, epochMax }: { histories: RunHistoryMap; runLabels?: Record<string, string>; epochMax?: number }) {
  const runIds = Object.keys(histories);
  const tasks = new Set<string>();
  for (const history of Object.values(histories)) {
    for (const e of history) {
      for (const task of ALL_TASKS) {
        if (e.val_metrics[task]) tasks.add(task);
      }
    }
  }

  return (
    <>
      {Array.from(tasks).map((task) => {
        const data = buildSeries(histories, (e) => {
          const m = e.val_metrics[task];
          if (!m || typeof m === "number") return 0;
          return (m.f1 ?? 0) * 100;
        });
        return (
          <TrainingChart
            key={task}
            title={`${task} — macro F1 (val)`}
            data={data}
            runIds={runIds}
            runLabels={runLabels}
            yFormatter={(v) => `${v.toFixed(1)}%`}
            domain={[0, 100]}
            epochMax={epochMax}
          />
        );
      })}
    </>
  );
}
