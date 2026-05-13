import {
  Box,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormGroup,
  FormControlLabel,
  Typography,
} from "@mui/material";
import type { RunInfo } from "@/types";

interface RunSelectorProps {
  runs: RunInfo[];
  loading: boolean;
  selectedIds: Set<string>;
  onToggle: (runId: string) => void;
  runLabels?: Record<string, string>;
}

function RunLabel({ run, label }: { run: RunInfo; label?: string }) {
  const displayName = label ?? run.run_id.replace(/^[^/]+\//, "");
  return (
    <Box sx={{ py: 0.25 }}>
      <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: 1.3 }}>
        {displayName}
      </Typography>
      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.25 }}>
        <Chip
          label={`ep${run.epochs_completed}`}
          size="small"
          sx={{ fontSize: 10, height: 18 }}
        />
        <Chip
          label={`acc ${(run.best_overall_acc * 100).toFixed(1)}%`}
          size="small"
          color="primary"
          variant="outlined"
          sx={{ fontSize: 10, height: 18 }}
        />
      </Box>
    </Box>
  );
}

// Group runs by dataset_version + phase
function groupRuns(runs: RunInfo[]): Record<string, RunInfo[]> {
  const groups: Record<string, RunInfo[]> = {};
  for (const run of runs) {
    const key = `${run.dataset_version} — Phase ${run.phase}`;
    (groups[key] ??= []).push(run);
  }
  return groups;
}

export function RunSelector({ runs, loading, selectedIds, onToggle, runLabels }: RunSelectorProps) {
  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", pt: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (runs.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary">
          No training runs found in outputs/
        </Typography>
      </Box>
    );
  }

  const groups = groupRuns(runs);

  return (
    <Box sx={{ pt: 0.5, pl: 1, pr: 0.5 }}>
      <Typography variant="overline" sx={{ color: "text.secondary" }}>
        Runs
      </Typography>
      {Object.entries(groups).map(([group, groupRuns]) => (
        <Box key={group}>
          <Divider sx={{ my: 1 }} />
          <Typography
            variant="caption"
            sx={{ pr: 1, color: "text.secondary", fontWeight: 600, display: "block" }}
          >
            {group}
          </Typography>
          <FormGroup>
            {groupRuns.map((run) => (
              <FormControlLabel
                key={run.run_id}
                sx={{ mx: 0, alignItems: "flex-start" }}
                control={
                  <Checkbox
                    size="small"
                    checked={selectedIds.has(run.run_id)}
                    onChange={() => onToggle(run.run_id)}
                    sx={{ pt: 0.5, pl: 0, pr: 0.5 }}
                  />
                }
                label={<RunLabel run={run} label={runLabels?.[run.run_id]} />}
              />
            ))}
          </FormGroup>
        </Box>
      ))}
    </Box>
  );
}
