import { Box, Typography } from "@mui/material";
import { AppShell } from "@/components/layout/AppShell";

export default function TrainingEvaluationPage() {
  return (
    <AppShell
      sidebar={<Box sx={{ p: 2 }} />}
      detail={
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          <Typography color="text.secondary" variant="h6">
            Training Evaluation — coming soon
          </Typography>
        </Box>
      }
    />
  );
}
