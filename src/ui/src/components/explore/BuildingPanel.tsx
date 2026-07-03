import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  Paper,
  Skeleton,
  Typography,
} from "@mui/material";
import { ExpandMore, ExpandLess } from "@mui/icons-material";
import { api } from "@/api/client";
import type { BuildingDetail } from "@/types";

// Attributes currently modelled (Tier 1 + Tier 2) — shown by default; values are bold
const TRAINED_ATTRIBUTES = new Set([
  "architectural_style",
  "building_form",
  "roof_type",
  "primary_cladding",
  "stories",
  "setting",
  "chimney_present",
]);

// Training tier for each attribute (drives the stage badge colour)
const ATTRIBUTE_TIER: Record<string, 1 | 2 | 3 | 4> = {
  // Tier 1
  stories: 1, roof_type: 1, primary_cladding: 1, setting: 1,
  chimney_present: 1, window: 1, entrance: 1,
  // Tier 2
  architectural_style: 2, building_form: 2, roof_features: 2,
  roof_materials: 2, additional_cladding: 2, wall_features: 2,
  landscape_features: 2, associated_buildings: 2,
  // Tier 3
  building_plan: 3, building_category: 3, current_use: 3, original_use: 3,
  // Tier 4
  alteration_level: 4, alterations_additions: 4, alterations_entrances: 4,
  alterations_roof: 4, alterations_cladding: 4, alterations_windows: 4,
};

const TIER_COLOR: Record<1 | 2 | 3 | 4, string> = {
  1: "#8fb892", // soft green
  2: "#85a5c8", // soft blue
  3: "#cfa07a", // soft orange
  4: "#c08888", // soft red
};

// Human-readable labels
const ATTRIBUTE_LABELS: Record<string, string> = {
  stories: "Stories", roof_type: "Roof Type", primary_cladding: "Primary Cladding",
  setting: "Setting", chimney_present: "Chimney Present", window: "Window", entrance: "Entrance",
  architectural_style: "Architectural Style", building_form: "Building Form",
  roof_features: "Roof Features", roof_materials: "Roof Materials",
  additional_cladding: "Additional Cladding", wall_features: "Wall Features",
  landscape_features: "Landscape Features", associated_buildings: "Associated Buildings",
  building_plan: "Building Plan", building_category: "Building Category",
  current_use: "Current Use", original_use: "Original Use",
  alteration_level: "Alteration Level", alterations_additions: "Alterations — Additions",
  alterations_entrances: "Alterations — Entrances", alterations_roof: "Alterations — Roof",
  alterations_cladding: "Alterations — Cladding", alterations_windows: "Alterations — Windows",
};

function toLabel(key: string): string {
  return ATTRIBUTE_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function TierBadge({ attrKey }: { attrKey: string }) {
  const tier = ATTRIBUTE_TIER[attrKey];
  if (!tier) return null;
  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 13,
        height: 13,
        borderRadius: "50%",
        bgcolor: TIER_COLOR[tier],
        flexShrink: 0,
        ml: 0.5,
      }}
    >
      <Typography component="span" sx={{ fontSize: "8px", color: "white", fontWeight: 700, lineHeight: 1 }}>
        {tier}
      </Typography>
    </Box>
  );
}

function AttributeGrid({ entries }: { entries: [string, string | null][] }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 1 }}>
      {entries.map(([key, value]) => {
        const trained = TRAINED_ATTRIBUTES.has(key);
        return (
          <Box key={key}>
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Typography
                variant="caption"
                sx={{ color: "grey.700" }}
              >
                {toLabel(key)}
              </Typography>
              <TierBadge attrKey={key} />
            </Box>
            <Typography variant="body2" sx={{ fontWeight: trained ? 600 : 400 }}>
              {value ?? "—"}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}

interface BuildingPanelProps {
  dataset: string;
  buildingId: string;
}

export function BuildingPanel({ dataset, buildingId }: BuildingPanelProps) {
  const [detail, setDetail] = useState<BuildingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    setDetail(null);
    setLoading(true);
    setError(null);
    setShowAll(false);
    api
      .getBuilding(dataset, buildingId)
      .then(setDetail)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [dataset, buildingId]);

  if (loading) {
    return (
      <Box>
        <Skeleton variant="text" width={200} height={40} />
        <Skeleton variant="rectangular" height={80} sx={{ mt: 1 }} />
        <Skeleton variant="rectangular" height={120} sx={{ mt: 2 }} />
      </Box>
    );
  }

  if (error) {
    return <Typography color="error">{error}</Typography>;
  }

  if (!detail) return null;

  const allEntries = Object.entries(detail.attributes) as [string, string | null][];
  const primaryEntries = allEntries.filter(([key]) => TRAINED_ATTRIBUTES.has(key));
  const extraEntries = allEntries.filter(([key]) => !TRAINED_ATTRIBUTES.has(key));

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700 }} gutterBottom>
        {detail.address ?? detail.building_id}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <Chip label={detail.dataset} size="small" color="primary" variant="outlined" />
        <Chip label={detail.neighborhood} size="small" />
        {detail.address && (
          <Typography variant="caption" color="text.secondary">
            {detail.building_id}
          </Typography>
        )}
      </Box>

      {/* Attributes */}
      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }} gutterBottom>
          Attributes
        </Typography>
        <Divider sx={{ mb: 1.5 }} />

        <AttributeGrid entries={primaryEntries} />

        {extraEntries.length > 0 && (
          <>
            <Button
              size="small"
              onClick={() => setShowAll((v) => !v)}
              endIcon={showAll ? <ExpandLess /> : <ExpandMore />}
              sx={{ mt: 1.5, color: "text.secondary", textTransform: "none" }}
            >
              {showAll ? "Hide" : `Show ${extraEntries.length} more attributes`}
            </Button>
            <Collapse in={showAll}>
              <Divider sx={{ my: 1.5 }} />
              <AttributeGrid entries={extraEntries} />
            </Collapse>
          </>
        )}
      </Paper>

      {/* Image pairs */}
      <Typography variant="subtitle2" sx={{ fontWeight: 600 }} gutterBottom>
        Images ({detail.images.length})
      </Typography>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {detail.images.map((img) => (
          <Paper key={img.filename} variant="outlined" sx={{ overflow: "hidden" }}>
            {/* Row header */}
            <Box
              sx={{
                px: 1.5,
                py: 0.75,
                bgcolor: "grey.50",
                borderBottom: 1,
                borderColor: "divider",
              }}
            >
              <Typography variant="caption" color="text.secondary">
                {img.filename}
              </Typography>
            </Box>

            {/* Side-by-side images */}
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: img.crop_url ? "1fr 1fr" : "1fr",
              }}
            >
              {/* Original */}
              <Box sx={{ borderRight: img.crop_url ? 1 : 0, borderColor: "divider" }}>
                <Box
                  sx={{
                    px: 1.5,
                    py: 0.5,
                    bgcolor: "primary.50",
                    borderBottom: 1,
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 600 }} color="primary.main">
                    ORIGINAL
                  </Typography>
                </Box>
                <Box
                  component="img"
                  src={img.original_url}
                  alt="original"
                  sx={{ width: "100%", display: "block", maxHeight: 260, objectFit: "contain", bgcolor: "white" }}
                />
              </Box>

              {/* Crop */}
              {img.crop_url && (
                <Box>
                  <Box
                    sx={{
                      px: 1.5,
                      py: 0.5,
                      bgcolor: "primary.50",
                      borderBottom: 1,
                      borderColor: "divider",
                    }}
                  >
                    <Typography variant="caption" sx={{ fontWeight: 600 }} color="primary.main">
                      CROPPED
                    </Typography>
                  </Box>
                  <Box
                    component="img"
                    src={img.crop_url}
                    alt="crop"
                    sx={{ width: "100%", display: "block", maxHeight: 260, objectFit: "contain", bgcolor: "white" }}
                  />
                </Box>
              )}
            </Box>
          </Paper>
        ))}
      </Box>
    </Box>
  );
}
