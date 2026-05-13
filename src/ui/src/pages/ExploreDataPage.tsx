import { useState, useEffect } from "react";
import { Box, Typography } from "@mui/material";
import { AppShell } from "@/components/layout/AppShell";
import { DatasetTree } from "@/components/explore/DatasetTree";
import { NeighborhoodPanel } from "@/components/explore/NeighborhoodPanel";
import { BuildingPanel } from "@/components/explore/BuildingPanel";
import { useDataset } from "@/context/DatasetContext";
import { useSearch } from "@/context/SearchContext";
import type {
  NeighborhoodStats,
  TreeSelection,
} from "@/types";
import { api } from "@/api/client";

export default function ExploreDataPage() {
  const { activeDataset } = useDataset();
  const { selectedBuilding, selectBuilding } = useSearch();
  const [selection, setSelection] = useState<TreeSelection | null>(null);
  const [neighborhoodStats, setNeighborhoodStats] = useState<NeighborhoodStats | null>(null);

  // Reset selection when dataset changes
  useEffect(() => {
    setSelection(null);
    setNeighborhoodStats(null);
  }, [activeDataset]);

  // When a building is selected via the TopBar search, apply it
  useEffect(() => {
    if (!selectedBuilding) return;
    setSelection({
      type: "building",
      dataset: activeDataset,
      neighborhood: selectedBuilding.neighborhood,
      building_id: selectedBuilding.building_id,
    });
    selectBuilding(null); // consume
  }, [selectedBuilding, activeDataset, selectBuilding]);

  // When a neighbourhood is selected, fetch its stats (already cached by backend)
  useEffect(() => {
    if (selection?.type !== "neighborhood") {
      setNeighborhoodStats(null);
      return;
    }
    api.listNeighborhoods(activeDataset).then((hoods) => {
      const found = hoods.find((h) => h.neighborhood === selection.neighborhood);
      setNeighborhoodStats(found ?? null);
    });
  }, [selection, activeDataset]);

  function handleSelect(sel: TreeSelection) {
    setSelection(sel);
  }

  function renderDetail() {
    if (!selection) {
      return (
        <Box
          sx={{
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography color="text.secondary">
            Select a neighbourhood, building, or image from the tree
          </Typography>
        </Box>
      );
    }

    if (selection.type === "neighborhood" && neighborhoodStats) {
      return <NeighborhoodPanel stats={neighborhoodStats} />;
    }

    if (selection.type === "building") {
      return (
        <BuildingPanel
          dataset={activeDataset}
          buildingId={selection.building_id}
        />
      );
    }

    return null;
  }

  return (
    <AppShell
      sidebar={
        <DatasetTree dataset={activeDataset} onSelect={handleSelect} selection={selection} />
      }
      detail={renderDetail()}
    />
  );
}
