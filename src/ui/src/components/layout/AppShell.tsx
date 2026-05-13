import { Box, Toolbar } from "@mui/material";

const SIDEBAR_WIDTH = 300;

interface AppShellProps {
  sidebar: React.ReactNode;
  detail: React.ReactNode;
}

export function AppShell({ sidebar, detail }: AppShellProps) {
  return (
    <Box sx={{ display: "flex", height: "100vh" }}>
      {/* Offset for fixed AppBar */}
      <Toolbar />

      {/* Sidebar */}
      <Box
        component="nav"
        sx={{
          width: SIDEBAR_WIDTH,
          flexShrink: 0,
          borderRight: 1,
          borderColor: "divider",
          overflowY: "auto",
          pt: 8, // below AppBar
          pb: 2,
        }}
      >
        {sidebar}
      </Box>

      {/* Detail panel */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          pt: 8, // below AppBar
          pb: 2,
          px: 3,
        }}
      >
        {detail}
      </Box>
    </Box>
  );
}
