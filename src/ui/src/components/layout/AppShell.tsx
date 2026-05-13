import { Box } from "@mui/material";

const SIDEBAR_WIDTH = 252;

interface AppShellProps {
  sidebar: React.ReactNode;
  detail: React.ReactNode;
}

export function AppShell({ sidebar, detail }: AppShellProps) {
  return (
    <Box sx={{ display: "flex", height: "100vh" }}>

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
          pl: 1,
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
          pl: 2,
          pr: 3,
        }}
      >
        {detail}
      </Box>
    </Box>
  );
}
