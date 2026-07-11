import { Alert, Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import CropIcon from "@mui/icons-material/Crop";
import type { ImageResult } from "@/types";
import { TaskResultCard } from "./TaskResultCard";
import { PHASE3_TASKS } from "./taskLabels";

const styles = {
  card: {
    mb: 2,
  },
  thumbnailStack: {
    flexShrink: 0,
    pr: 2,
  },
  thumbnailBox: {
    textAlign: "center",
  },
  originalImg: {
    width: 100,
    height: 75,
    objectFit: "cover",
    borderRadius: 1,
    cursor: "zoom-in",
    border: 1,
    borderColor: "divider",
    display: "block",
    "&:hover": { opacity: 0.85 },
  },
  croppedImg: {
    width: 100,
    height: 75,
    objectFit: "cover",
    borderRadius: 1,
    cursor: "zoom-in",
    border: 2,
    borderColor: "info.main",
    display: "block",
    "&:hover": { opacity: 0.85 },
  },
  autoCropChip: {
    fontSize: "0.6rem",
    height: 16,
    alignSelf: "center",
    ml: 1,
    "& .MuiChip-label": { px: 0.5 },
  },
  cropIcon: {
    fontSize: "0.75rem !important",
  },
  taskGrid: {
    display: "grid",
    gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
    gap: 2,
  },
  columnHeading: {
    mb: 1,
    color: "text.secondary",
  },
} as const;

export function ImageResultPanel({
  result,
  previewUrl,
  label,
  onImageClick,
  compactResults = false,
}: {
  result: ImageResult;
  previewUrl?: string;
  label: string;
  onImageClick: (src: string) => void;
  compactResults?: boolean;
}) {
  const croppedSrc = result.cropped_image_b64
    ? `data:image/jpeg;base64,${result.cropped_image_b64}`
    : null;
  const phase12Tasks = result.tasks.filter((t) => !PHASE3_TASKS.has(t.task));
  const phase3Tasks = result.tasks.filter((t) => PHASE3_TASKS.has(t.task));
  const hasPhase3 = phase3Tasks.length > 0;
  const noBuildingDetected = result.building_detected === false;

  return (
    <Card variant="outlined" sx={styles.card}>
      <CardContent>
        <Stack direction="row" sx={{ gap: 3, alignItems: "flex-start" }}>
          {/* Thumbnails — original and/or cropped */}
          <Stack direction="row" sx={{ ...styles.thumbnailStack, gap: 1 }}>
            {previewUrl && (
              <Box sx={styles.thumbnailBox}>
                <Box
                  component="img"
                  src={previewUrl}
                  alt="Original"
                  onClick={() => onImageClick(previewUrl)}
                  sx={styles.originalImg}
                />
                <Typography variant="caption" color="text.secondary">
                  Original
                </Typography>
              </Box>
            )}
            {croppedSrc && (
              <Box sx={styles.thumbnailBox}>
                <Box
                  component="img"
                  src={croppedSrc}
                  alt="Cropped"
                  onClick={() => onImageClick(croppedSrc)}
                  sx={styles.croppedImg}
                />
                <Typography variant="caption" color="info.main">
                  Cropped
                </Typography>
              </Box>
            )}
          </Stack>

          <Box sx={{ flex: 1 }}>
            <Stack direction="row" sx={{ alignItems: "center", gap: 1, mb: 1.5 }}>
              <Typography variant="subtitle1" sx={{ color: "text.primary", fontWeight: 700 }}>
                {label}
              </Typography>
              {result.auto_cropped && (
                <Chip
                  icon={<CropIcon sx={styles.cropIcon} />}
                  label="auto-cropped"
                  size="small"
                  color="info"
                  variant="outlined"
                  sx={styles.autoCropChip}
                />
              )}
            </Stack>
            {noBuildingDetected ? (
              <Alert severity="info" sx={{ mt: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {result.message ?? "No building detected"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Try a clearer exterior building photo.
                </Typography>
              </Alert>
            ) : hasPhase3 ? (
              <Box sx={styles.taskGrid}>
                <Box>
                  <Typography variant="caption" sx={{ ...styles.columnHeading, fontWeight: 700 }}>
                    Phase 1 / 2
                  </Typography>
                  {phase12Tasks.map((t, i) => (
                    <TaskResultCard key={t.task} result={t} divider={i > 0} compact={compactResults} />
                  ))}
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ ...styles.columnHeading, fontWeight: 700 }}>
                    Phase 3
                  </Typography>
                  {phase3Tasks.map((t, i) => (
                    <TaskResultCard key={t.task} result={t} divider={i > 0} compact={compactResults} />
                  ))}
                </Box>
              </Box>
            ) : (
              result.tasks.map((t, i) => (
                <TaskResultCard key={t.task} result={t} divider={i > 0} compact={compactResults} />
              ))
            )}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
