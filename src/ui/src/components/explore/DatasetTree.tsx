import { useEffect, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { SimpleTreeView, TreeItem } from "@mui/x-tree-view";
import { ApartmentOutlined, LocationCityOutlined } from "@mui/icons-material";
import { Box, CircularProgress, Typography } from "@mui/material";
import { api } from "@/api/client";
import type { BuildingSummary, NeighborhoodStats, TreeSelection } from "@/types";

// ---------------------------------------------------------------------------
// VirtualBuildingList — uses @tanstack/react-virtual so only ~20 DOM nodes
// exist at a time regardless of how many buildings are in the neighbourhood.
// ---------------------------------------------------------------------------
const ITEM_HEIGHT = 32; // px — fixed row height
const MAX_VISIBLE_ROWS = 20; // max rows shown before scrolling kicks in
const MAX_CONTAINER_HEIGHT = MAX_VISIBLE_ROWS * ITEM_HEIGHT; // 640px

interface VirtualBuildingListProps {
  buildings: BuildingSummary[];
  dataset: string;
  onSelect: (selection: TreeSelection) => void;
}

function VirtualBuildingList({ buildings, dataset, onSelect }: VirtualBuildingListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: buildings.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ITEM_HEIGHT,
    overscan: 5,
  });

  const containerHeight = Math.min(buildings.length * ITEM_HEIGHT, MAX_CONTAINER_HEIGHT);

  return (
    <Box sx={{ pl: 1 }}>
      <Box
        ref={parentRef}
        sx={{ height: containerHeight, overflowY: "auto" }}
      >
        <Box sx={{ height: virtualizer.getTotalSize(), position: "relative" }}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const building = buildings[virtualRow.index];
            return (
              <Box
                key={building.building_id}
                onClick={() => onSelect({ type: "building", dataset, building_id: building.building_id })}
                sx={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  right: 0,
                  transform: `translateY(${virtualRow.start}px)`,
                  display: "flex",
                  alignItems: "center",
                  gap: 0.5,
                  height: ITEM_HEIGHT,
                  px: 1,
                  cursor: "pointer",
                  borderRadius: 1,
                  "&:hover": { bgcolor: "action.hover" },
                }}
              >
                <ApartmentOutlined fontSize="small" color="action" sx={{ flexShrink: 0 }} />
                <Typography variant="body2" noWrap sx={{ flex: 1, minWidth: 0 }}>
                  {building.address ?? building.building_id}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
                  {building.image_count}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
}

interface DatasetTreeProps {
  dataset: string;
  onSelect: (selection: TreeSelection) => void;
}

export function DatasetTree({ dataset, onSelect }: DatasetTreeProps) {
  const [neighborhoods, setNeighborhoods] = useState<NeighborhoodStats[]>([]);
  const [buildings, setBuildings] = useState<Record<string, BuildingSummary[]>>({});
  const [loadingHoods, setLoadingHoods] = useState(true);
  const [loadingBuildings, setLoadingBuildings] = useState<Set<string>>(new Set());
  const [expandedHoods, setExpandedHoods] = useState<Set<string>>(new Set());

  useEffect(() => {
    setNeighborhoods([]);
    setBuildings({});
    setExpandedHoods(new Set());
    setLoadingHoods(true);
    api
      .listNeighborhoods(dataset)
      .then(setNeighborhoods)
      .catch(console.error)
      .finally(() => setLoadingHoods(false));
  }, [dataset]);

  function handleExpandedChange(_event: React.SyntheticEvent | null, nodeIds: string[]) {
    const newlyExpanded = nodeIds.filter((id) => !expandedHoods.has(id));
    setExpandedHoods(new Set(nodeIds));

    for (const nodeId of newlyExpanded) {
      if (!nodeId.startsWith("hood:")) continue;
      const hood = nodeId.slice(5);
      if (buildings[hood]) continue;

      setLoadingBuildings((prev) => new Set(prev).add(hood));
      api
        .listBuildings(dataset, hood)
        .then((data) => setBuildings((prev) => ({ ...prev, [hood]: data })))
        .catch(console.error)
        .finally(() =>
          setLoadingBuildings((prev) => {
            const next = new Set(prev);
            next.delete(hood);
            return next;
          })
        );
    }
  }

  if (loadingHoods) {
    return (
      <Box sx={{ p: 2, display: "flex", alignItems: "center", gap: 1 }}>
        <CircularProgress size={16} />
        <Typography variant="body2" color="text.secondary">
          Loading...
        </Typography>
      </Box>
    );
  }

  return (
    <SimpleTreeView onExpandedItemsChange={handleExpandedChange} sx={{ p: 1 }}>
      {neighborhoods.map((hood) => (
        <TreeItem
          key={`hood:${hood.neighborhood}`}
          itemId={`hood:${hood.neighborhood}`}
          label={
            <Box
              sx={{ display: "flex", alignItems: "center", gap: 0.5, py: 0.25 }}
              onClick={() =>
                onSelect({ type: "neighborhood", dataset, neighborhood: hood.neighborhood })
              }
            >
              <LocationCityOutlined fontSize="small" color="action" />
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {hood.neighborhood}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
                {hood.building_count}
              </Typography>
            </Box>
          }
        >
          {loadingBuildings.has(hood.neighborhood) || !buildings[hood.neighborhood] ? (
            <TreeItem
              itemId={`loading:${hood.neighborhood}`}
              label={
                loadingBuildings.has(hood.neighborhood) ? (
                  <CircularProgress size={12} sx={{ my: 0.5 }} />
                ) : (
                  <Typography variant="caption" color="text.secondary" sx={{ py: 0.5 }}>
                    Loading...
                  </Typography>
                )
              }
            />
          ) : (
            <VirtualBuildingList
              buildings={buildings[hood.neighborhood]}
              dataset={dataset}
              onSelect={onSelect}
            />
          )}
        </TreeItem>
      ))}
    </SimpleTreeView>
  );
}
