import {
  AppBar,
  Autocomplete,
  Box,
  CircularProgress,
  FormControl,
  MenuItem,
  Select,
  Tab,
  Tabs,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useDataset } from "@/context/DatasetContext";
import { useSearch } from "@/context/SearchContext";
import { api } from "@/api/client";
import type { BuildingSummary } from "@/types";

const NAV_TABS = [
  { label: "Explore", path: "/" },
  { label: "Training", path: "/training" },
  { label: "Inference", path: "/inference" },
];

export function TopBar() {
  const { datasets, activeDataset, setActiveDataset, loading } = useDataset();
  const { selectBuilding } = useSearch();
  const location = useLocation();
  const navigate = useNavigate();
  const isExplore = location.pathname === "/";

  const [inputValue, setInputValue] = useState("");
  const [options, setOptions] = useState<BuildingSummary[]>([]);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const tabIndex = NAV_TABS.findIndex((t) => t.path === location.pathname);
  const activeTab = tabIndex === -1 ? 0 : tabIndex;

  function handleDatasetChange(e: SelectChangeEvent) {
    setActiveDataset(e.target.value);
    setInputValue("");
    setOptions([]);
  }

  function handleTabChange(_: React.SyntheticEvent, newValue: number) {
    navigate(NAV_TABS[newValue].path);
  }

  const fetchOptions = useCallback((q: string) => {
    if (q.length < 2) { setOptions([]); return; }
    setSearching(true);
    api.searchBuildings(activeDataset, q, 10)
      .then(setOptions)
      .finally(() => setSearching(false));
  }, [activeDataset]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchOptions(inputValue), 250);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [inputValue, fetchOptions]);

  return (
    <AppBar position="fixed" color="primary" elevation={1}>
      <Toolbar sx={{ gap: 2 }}>
        {/* Logo */}
        <Box
          sx={{
            width: 44,
            height: 44,
            borderRadius: "50%",
            bgcolor: "rgb(196,195,192)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            flexShrink: 0,
          }}
        >
          <Box
            component="img"
            src="/logo.png"
            alt="Arepas logo"
            sx={{ width: 58, height: 58, objectFit: "contain" }}
          />
        </Box>
        <Typography variant="h6" component="div" sx={{ fontWeight: 700, letterSpacing: 1, flexShrink: 0 }}>
          Arepas
        </Typography>

        {/* Page navigation */}
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          textColor="inherit"
          TabIndicatorProps={{ style: { backgroundColor: "white" } }}
          sx={{ ml: 3 }}
        >
          {NAV_TABS.map((tab) => (
            <Tab
              key={tab.path}
              label={tab.label}
              sx={{ opacity: 0.75, "&.Mui-selected": { opacity: 1 } }}
            />
          ))}
        </Tabs>

        <Box sx={{ flexGrow: 1 }} />

        {/* Building search — Explore page only */}
        {isExplore && (
          <Autocomplete<BuildingSummary>
            options={options}
            inputValue={inputValue}
            onInputChange={(_, v) => setInputValue(v)}
            onChange={(_, value) => {
              if (value) {
                selectBuilding(value);
                setInputValue("");
                setOptions([]);
              }
            }}
            getOptionLabel={(o) => o.address ?? o.building_id}
            getOptionKey={(o) => o.building_id}
            filterOptions={(x) => x}
            loading={searching}
            noOptionsText={inputValue.length < 2 ? "Type to search…" : "No buildings found"}
            size="small"
            sx={{ width: 240 }}
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder="Search buildings…"
                variant="outlined"
                sx={{
                  "& .MuiOutlinedInput-root": {
                    color: "white",
                    "& fieldset": { borderColor: "rgba(255,255,255,0.4)" },
                    "&:hover fieldset": { borderColor: "rgba(255,255,255,0.7)" },
                  },
                  "& .MuiInputBase-input::placeholder": { color: "rgba(255,255,255,0.6)", opacity: 1 },
                  "& .MuiSvgIcon-root": { color: "rgba(255,255,255,0.7)" },
                }}
              />
            )}
            renderOption={(props, option) => (
              <Box component="li" {...props}>
                <Box>
                  <Typography variant="body2">{option.address ?? option.building_id}</Typography>
                  {option.address && (
                    <Typography variant="caption" color="text.secondary">{option.building_id}</Typography>
                  )}
                </Box>
              </Box>
            )}
          />
        )}

        {/* Dataset picker */}
        {loading ? (
          <CircularProgress size={20} color="inherit" />
        ) : (
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <Select
              value={activeDataset}
              onChange={handleDatasetChange}
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
