import { Box, Chip, LinearProgress, Stack, Typography } from "@mui/material";
import type { TaskResult } from "@/types";
import { taskLabel } from "./taskLabels";

const styles = {
  wrapper: (divider: boolean) => ({
    pt: divider ? 3 : 0,
    mt: divider ? 0.25 : 0,
    borderTop: divider ? "1px solid" : "none",
    borderColor: "divider",
  }),
  labelText: {
    minWidth: 160,
    color: "grey.700",
  },
  confidenceChip: {
    fontWeight: 700,
    fontSize: "0.65rem",
    height: 18,
    ml: 0.75,
    "& .MuiChip-label": { px: 0.75 },
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
    mb: 0.5,
  },
  top3Item: {
    color: "grey.700",
    display: "flex",
    alignItems: "center",
  },
  top3Dot: {
    mx: 1,
    opacity: 0.35,
  },
} as const;

const MULTI_LABEL_DISPLAY_THRESHOLD = 50;

export function TaskResultCard({
  result,
  divider = false,
  compact = false,
}: {
  result: TaskResult;
  divider?: boolean;
  compact?: boolean;
}) {
  const conf = result.confidence;
  const color = conf >= 70 ? "success" : conf >= 45 ? "warning" : "error";

  return (
    <Box sx={styles.wrapper(divider)}>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 0.5 }}>
        <Typography variant="body2" sx={{ ...styles.labelText, fontWeight: 600 }}>
          {taskLabel(result.task)}
        </Typography>
        <Stack direction="row" sx={{ alignItems: "center", gap: 1 }}>
          {compact && result.is_multi_label ? (
            <Typography variant="body2" color={`${color}.main`} sx={{ fontWeight: 700, textAlign: "right" }}>
              {(result.top3.filter((t) => t.confidence >= MULTI_LABEL_DISPLAY_THRESHOLD).map((t) => t.label).join(" · ")) || result.predicted}
            </Typography>
          ) : (
            <Typography variant="body2" color={`${color}.main`} sx={{ fontWeight: 700 }}>
              {result.predicted}
            </Typography>
          )}
          {!compact && (
            <Chip
              label={`${conf.toFixed(1)}%`}
              size="small"
              color={color}
              variant="outlined"
              sx={styles.confidenceChip}
            />
          )}
        </Stack>
      </Stack>
      <LinearProgress
        variant="determinate"
        value={conf}
        color={color}
        sx={styles.progressBar}
      />
      {!compact && (
        <Stack direction="row" sx={{ gap: 0, flexWrap: "wrap" }}>
          {result.top3.map((item, i) => (
            <Typography key={item.label} variant="caption" sx={styles.top3Item}>
              {i > 0 && <Box component="span" sx={styles.top3Dot}>·</Box>}
              <Box component="span" sx={{ fontWeight: 700 }}>{item.label}</Box>&nbsp;{item.confidence.toFixed(1)}%
            </Typography>
          ))}
        </Stack>
      )}
    </Box>
  );
}
