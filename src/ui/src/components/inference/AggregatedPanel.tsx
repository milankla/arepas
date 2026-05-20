import { Card, CardContent, Typography } from "@mui/material";
import type { TaskResult } from "@/types";
import { TaskResultCard } from "./TaskResultCard";

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
} as const;

export function AggregatedPanel({ tasks }: { tasks: TaskResult[] }) {
  return (
    <Card variant="outlined" sx={styles.card}>
      <CardContent>
        <Typography variant="h6" fontWeight={700} sx={styles.heading}>
          Aggregated (all images)
        </Typography>
        {tasks.map((t, i) => (
          <TaskResultCard key={t.task} result={t} divider={i > 0} />
        ))}
      </CardContent>
    </Card>
  );
}
