import {
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { useRef } from "react";
import type { CheckpointInfo } from "@/types";

const styles = {
  root: {
    p: 1.5,
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  dropZone: {
    border: "2px dashed",
    borderColor: "divider",
    borderRadius: 2,
    p: 2,
    textAlign: "center",
    cursor: "pointer",
    transition: "border-color 0.2s",
    "&:hover": { borderColor: "primary.main" },
  },
  thumbnail: {
    width: 40,
    height: 30,
    objectFit: "cover",
    borderRadius: 0.5,
    flexShrink: 0,
    mr: 1,
  },
  removeBtn: {
    minWidth: 0,
    p: 0.25,
    fontSize: "0.7rem",
    ml: 1,
  },
  ckptChip: {
    fontSize: "0.6rem",
    height: 16,
    ml: 0.5,
    "& .MuiChip-label": { px: 0.75 },
  },
  phaseCheckbox: {
    m: 0,
    gap: 0.25,
  },
} as const;

export function InferenceSidebar({
  checkpoints,
  loadingCkpts,
  selectedCkpt,
  onSelectCkpt,
  phaseFilter,
  onTogglePhase,
  files,
  previews,
  onAddFiles,
  onRemoveFile,
  onClearFiles,
  running,
  onRun,
  medalMap,
}: {
  checkpoints: CheckpointInfo[];
  loadingCkpts: boolean;
  selectedCkpt: string;
  onSelectCkpt: (path: string) => void;
  phaseFilter: Set<number>;
  onTogglePhase: (phase: number) => void;
  files: File[];
  previews: string[];
  onAddFiles: (files: FileList | File[] | null) => void;
  onRemoveFile: (idx: number) => void;
  onClearFiles: () => void;
  running: boolean;
  onRun: () => void;
  medalMap: Record<string, string>;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const visibleCheckpoints = checkpoints.filter((c) => phaseFilter.has(c.phase));

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    onAddFiles(e.dataTransfer.files);
  }

  return (
    <Box sx={styles.root}>
      <Typography variant="subtitle1" fontWeight={700}>
        Inference
      </Typography>

      {/* Checkpoint selector */}
      {loadingCkpts ? (
        <CircularProgress size={20} />
      ) : (
        <FormControl fullWidth size="small">
          <InputLabel>Model checkpoint</InputLabel>
          <Select
            label="Model checkpoint"
            value={visibleCheckpoints.some((c) => c.checkpoint_path === selectedCkpt) ? selectedCkpt : ""}
            onChange={(e: SelectChangeEvent) => onSelectCkpt(e.target.value)}
          >
            {visibleCheckpoints.map((ckpt) => (
              <MenuItem key={ckpt.checkpoint_path} value={ckpt.checkpoint_path}>
                <Box sx={{ width: "100%" }}>
                  <Stack direction="row" alignItems="center" gap={0.75}>
                    <Typography variant="body2" fontWeight={700} noWrap flex={1}>
                      {ckpt.short_name}
                    </Typography>
                    {medalMap[ckpt.checkpoint_path] && (
                      <Box component="span" sx={{ fontSize: "1rem", lineHeight: 1, flexShrink: 0 }}>
                        {medalMap[ckpt.checkpoint_path]}
                      </Box>
                    )}
                    <Chip
                      label={`ph${ckpt.phase}`}
                      size="small"
                      variant="outlined"
                      sx={styles.ckptChip}
                    />
                    <Chip
                      label={ckpt.input_type}
                      size="small"
                      color={ckpt.input_type === "paired" ? "success" : ckpt.input_type === "crop" ? "info" : "default"}
                      sx={styles.ckptChip}
                    />
                  </Stack>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {/* Phase filter */}
      <Stack direction="row" gap={1}>
        {[1, 2, 3].map((ph) => (
          <FormControlLabel
            key={ph}
            label={<Typography variant="caption">Phase {ph}</Typography>}
            control={
              <Checkbox
                size="small"
                checked={phaseFilter.has(ph)}
                onChange={() => onTogglePhase(ph)}
                sx={{ p: 0.5 }}
              />
            }
            sx={styles.phaseCheckbox}
          />
        ))}
      </Stack>

      <Divider />

      {/* Drop zone */}
      <Box
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileInputRef.current?.click()}
        sx={styles.dropZone}
      >
        <CloudUploadIcon sx={{ color: "text.secondary", mb: 0.5 }} />
        <Typography variant="body2" color="text.secondary">
          Drop images here or click to browse
        </Typography>
        <Typography variant="caption" color="text.disabled">
          JPEG / PNG · 1 or more images
        </Typography>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={(e) => onAddFiles(e.target.files)}
        />
      </Box>

      {/* Selected file list */}
      {files.length > 0 && (
        <Stack gap={1}>
          {files.map((f, i) => (
            <Stack key={i} direction="row" alignItems="center" gap={0}>
              <Box component="img" src={previews[i]} sx={styles.thumbnail} />
              <Typography variant="caption" flex={1} noWrap title={f.name} sx={{ alignSelf: "center" }}>
                {f.name}
              </Typography>
              <Button size="small" color="error" sx={styles.removeBtn} onClick={() => onRemoveFile(i)}>
                ✕
              </Button>
            </Stack>
          ))}
          <Button variant="text" size="small" color="error" onClick={onClearFiles}>
            Clear all
          </Button>
        </Stack>
      )}

      <Button
        variant="contained"
        disabled={!selectedCkpt || files.length === 0 || running}
        onClick={onRun}
        startIcon={running ? <CircularProgress size={14} color="inherit" /> : undefined}
      >
        {running ? "Running…" : "Run inference"}
      </Button>
    </Box>
  );
}
