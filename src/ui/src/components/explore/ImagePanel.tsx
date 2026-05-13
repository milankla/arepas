import { Box, Chip, Paper, Typography } from "@mui/material";
import type { BuildingImage } from "@/types";

interface ImagePanelProps {
  image: BuildingImage;
  buildingId: string;
}

export function ImagePanel({ image, buildingId }: ImagePanelProps) {
  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 700 }} gutterBottom noWrap>
        {image.filename}
      </Typography>
      <Chip label={buildingId} size="small" sx={{ mb: 2 }} />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: image.crop_url ? "1fr 1fr" : "1fr",
          gap: 2,
        }}
      >
        {/* Original */}
        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          <Box
            sx={{
              bgcolor: "grey.100",
              px: 1.5,
              py: 0.75,
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
            src={image.original_url}
            alt="original"
            sx={{ width: "100%", display: "block", maxHeight: "70vh", objectFit: "contain" }}
          />
        </Paper>

        {/* Crop */}
        {image.crop_url ? (
          <Paper variant="outlined" sx={{ overflow: "hidden" }}>
            <Box
              sx={{
                bgcolor: "primary.50",
                px: 1.5,
                py: 0.75,
                borderBottom: 1,
                borderColor: "divider",
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              <Typography variant="caption" sx={{ fontWeight: 600 }} color="primary.main">
                CROPPED
              </Typography>
            </Box>
            <Box
              component="img"
              src={image.crop_url}
              alt="cropped"
              sx={{ width: "100%", display: "block", maxHeight: "70vh", objectFit: "contain" }}
            />
          </Paper>
        ) : (
          <Paper
            variant="outlined"
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 200,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              No crop available for this image
            </Typography>
          </Paper>
        )}
      </Box>
    </Box>
  );
}
