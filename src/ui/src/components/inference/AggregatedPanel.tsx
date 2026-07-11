import { Box, Card, CardContent, Typography } from "@mui/material";
import type { TaskResult } from "@/types";
import { TaskResultCard } from "./TaskResultCard";
import { PHASE3_TASKS } from "./taskLabels";

const styles = {
  card: {
    mb: 2,
    borderColor: "primary.main",
    borderWidth: 2,
  },
  heading: {
    mb: 1.5,
    color: "text.primary",
  },
  taskGrid: {
    display: "grid",
    gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
    gap: 2,
  },
  columnHeading: {
    mb: 1,
    color: "text.secondary",
  },
} as const;

export function AggregatedPanel({ tasks, compact = false }: { tasks: TaskResult[]; compact?: boolean }) {
  const phase12Tasks = tasks.filter((t) => !PHASE3_TASKS.has(t.task));
  const phase3Tasks = tasks.filter((t) => PHASE3_TASKS.has(t.task));

  if (phase3Tasks.length === 0) {
    return (
      <Card variant="outlined" sx={styles.card}>
        <CardContent>
          <Typography variant="h6" sx={{ ...styles.heading, fontWeight: 700 }}>
            Aggregated (all images)
          </Typography>
          {tasks.map((t, i) => (
            <TaskResultCard key={t.task} result={t} divider={i > 0} compact={compact} />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="outlined" sx={styles.card}>
      <CardContent>
        <Typography variant="h6" sx={{ ...styles.heading, fontWeight: 700 }}>
          Aggregated (all images)
        </Typography>
        <Box sx={styles.taskGrid}>
          <Box>
            <Typography variant="caption" sx={{ ...styles.columnHeading, fontWeight: 700 }}>
              Phase 1 / 2
            </Typography>
            {phase12Tasks.map((t, i) => (
              <TaskResultCard key={t.task} result={t} divider={i > 0} compact={compact} />
            ))}
          </Box>
          <Box>
            <Typography variant="caption" sx={{ ...styles.columnHeading, fontWeight: 700 }}>
              Phase 3
            </Typography>
            {phase3Tasks.map((t, i) => (
              <TaskResultCard key={t.task} result={t} divider={i > 0} compact={compact} />
            ))}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}
