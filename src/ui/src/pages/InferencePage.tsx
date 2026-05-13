import { Box, Typography } from "@mui/material";
import { AppShell } from "@/components/layout/AppShell";

export default function InferencePage() {
  return (
    <AppShell
      sidebar={<Box sx={{ p: 2 }} />}
      detail={
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          <Typography color="text.secondary" variant="h6">
            Inference — coming soon
          </Typography>
        </Box>
      }
    />
  );
}
