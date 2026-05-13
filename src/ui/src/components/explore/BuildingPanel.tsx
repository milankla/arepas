import { useEffect, useState } from "react";
import {
  Box,
  Chip,
  Divider,
  Paper,
  Skeleton,
  Typography,
} from "@mui/material";
import { api } from "@/api/client";
import type { BuildingDetail } from "@/types";

// Human-readable labels for attribute columns
const ATTRIBUTE_LABELS: Record<string, string> = {
  architectural_style: "Architectural Style",
  building_form: "Building Form",
  roof_type: "Roof Type",
  primary_cladding: "Primary Cladding",
  stories: "Stories",
  alteration_level: "Alteration Level",
  setting: "Setting",
  chimney_present: "Chimney Present",
};

interface BuildingPanelProps {
  dataset: string;
  buildingId: string;
}

export function BuildingPanel({ dataset, buildingId }: BuildingPanelProps) {
  const [detail, setDetail] = useState<BuildingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDetail(null);
    setLoading(true);
    setError(null);
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

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700 }} gutterBottom>
        {detail.address ?? detail.building_id}
      </Typography>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
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
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 1,
          }}
        >
          {Object.entries(detail.attributes).map(([key, value]) => (
            <Box key={key}>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                {ATTRIBUTE_LABELS[key] ?? key}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {value ?? "—"}
              </Typography>
            </Box>
          ))}
        </Box>
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
                    bgcolor: "grey.100",
                    borderBottom: 1,
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="caption" sx={{ fontWeight: 600 }} color="text.secondary">
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
