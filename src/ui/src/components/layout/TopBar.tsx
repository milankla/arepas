import {
  AppBar,
  CircularProgress,
  FormControl,
  MenuItem,
  Select,
  Toolbar,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import { useDataset } from "@/context/DatasetContext";

export function TopBar() {
  const { datasets, activeDataset, setActiveDataset, loading } = useDataset();

  function handleChange(e: SelectChangeEvent) {
    setActiveDataset(e.target.value);
  }

  return (
    <AppBar position="fixed" color="primary" elevation={1}>
      <Toolbar sx={{ gap: 2 }}>
        <Typography variant="h6" component="div" sx={{ fontWeight: 700, letterSpacing: 1 }}>
          Arepas
        </Typography>

        {loading ? (
          <CircularProgress size={20} color="inherit" />
        ) : (
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <Select
              value={activeDataset}
              onChange={handleChange}
              displayEmpty
              sx={{ color: "white", ".MuiOutlinedInput-notchedOutline": { borderColor: "rgba(255,255,255,0.4)" } }}
            >
              {datasets.map((ds) => (
                <MenuItem key={ds.id} value={ds.id}>
                  {ds.label} — {ds.building_count} bldgs
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Toolbar>
    </AppBar>
  );
}
