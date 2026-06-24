import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
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
}: {
  result: ImageResult;
  previewUrl?: string;
  label: string;
  onImageClick: (src: string) => void;
}) {
  const croppedSrc = result.cropped_image_b64
    ? `data:image/jpeg;base64,${result.cropped_image_b64}`
    : null;
  const phase12Tasks = result.tasks.filter((t) => !PHASE3_TASKS.has(t.task));
  const phase3Tasks = result.tasks.filter((t) => PHASE3_TASKS.has(t.task));
  const hasPhase3 = phase3Tasks.length > 0;

  return (
    <Card variant="outlined" sx={styles.card}>
      <CardContent>
        <Stack direction="row" gap={3} alignItems="flex-start">
          {/* Thumbnails — original and/or cropped */}
          <Stack direction="row" gap={1} sx={styles.thumbnailStack}>
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

          <Box flex={1}>
            <Stack direction="row" alignItems="center" gap={1} sx={{ mb: 1.5 }}>
              <Typography variant="subtitle1" fontWeight={700} sx={{ color: "text.primary" }}>
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
            {hasPhase3 ? (
              <Box sx={styles.taskGrid}>
                <Box>
                  <Typography variant="caption" fontWeight={700} sx={styles.columnHeading}>
                    Phase 1 / 2
                  </Typography>
                  {phase12Tasks.map((t, i) => (
                    <TaskResultCard key={t.task} result={t} divider={i > 0} />
                  ))}
                </Box>
                <Box>
                  <Typography variant="caption" fontWeight={700} sx={styles.columnHeading}>
                    Phase 3
                  </Typography>
                  {phase3Tasks.map((t, i) => (
                    <TaskResultCard key={t.task} result={t} divider={i > 0} />
                  ))}
                </Box>
              </Box>
            ) : (
              result.tasks.map((t, i) => (
                <TaskResultCard key={t.task} result={t} divider={i > 0} />
              ))
            )}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
