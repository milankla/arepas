import { Alert, Box, Chip, CircularProgress, Typography } from "@mui/material";
import CropIcon from "@mui/icons-material/Crop";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/api/client";
import type { CheckpointInfo, InferenceResponse } from "@/types";
import { AggregatedPanel } from "@/components/inference/AggregatedPanel";
import { ImageResultPanel } from "@/components/inference/ImageResultPanel";
import { InferenceSidebar } from "@/components/inference/InferenceSidebar";
import { LightboxDialog } from "@/components/inference/LightboxDialog";

const styles = {
  emptyState: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "60vh",
  },
  loadingState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    mt: 8,
    gap: 2,
  },
  detail: {
    p: 1,
  },
  perImageLabel: {
    mb: 1,
    color: "grey.700",
  },
} as const;

export default function InferencePage() {
  const [checkpoints, setCheckpoints] = useState<CheckpointInfo[]>([]);
  const [loadingCkpts, setLoadingCkpts] = useState(true);
  const [selectedCkpt, setSelectedCkpt] = useState<string>("");
  const [phaseFilter, setPhaseFilter] = useState<Set<number>>(new Set([2]));

  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<InferenceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  function togglePhase(phase: number) {
    setPhaseFilter((prev) => {
      const next = new Set(prev);
      if (next.has(phase)) {
        if (next.size === 1) return prev;
        next.delete(phase);
      } else {
        next.add(phase);
      }
      return next;
    });
  }

  useEffect(() => {
    api.listCheckpoints()
      .then((ckpts) => {
        setCheckpoints(ckpts);
        const ph2 = ckpts.find((c) => c.phase === 2) ?? ckpts[0];
        if (ph2) setSelectedCkpt(ph2.checkpoint_path);
      })
      .catch(() => setError("Failed to load checkpoints."))
      .finally(() => setLoadingCkpts(false));
  }, []);

  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach(URL.revokeObjectURL);
  }, [files]);

  const addFiles = useCallback((newFiles: FileList | File[] | null) => {
    if (!newFiles) return;
    const imageFiles = Array.from(newFiles).filter((f) => f.type.startsWith("image/"));
    if (imageFiles.length === 0) return;
    setFiles((prev) => [...prev, ...imageFiles]);
    setResult(null);
    setError(null);
  }, []);

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
    setResult(null);
  }

  async function handleRun() {
    if (!selectedCkpt || files.length === 0) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.runInference(selectedCkpt, files);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Inference failed.");
    } finally {
      setRunning(false);
    }
  }

  const medalMap = useMemo(() => {
    const visible = checkpoints.filter((c) => phaseFilter.has(c.phase));
    const sorted = [...visible].sort((a, b) => b.best_overall_acc - a.best_overall_acc);
    const medals: Record<string, string> = {};
    ["🥇", "🥈", "🥉"].forEach((m, i) => {
      if (sorted[i]) medals[sorted[i].checkpoint_path] = m;
    });
    return medals;
  }, [checkpoints, phaseFilter]);

  const activeCkpt = useMemo(
    () => checkpoints.find((c) => c.checkpoint_path === selectedCkpt) ?? null,
    [checkpoints, selectedCkpt]
  );

  const sidebar = (
    <InferenceSidebar
      checkpoints={checkpoints}
      loadingCkpts={loadingCkpts}
      selectedCkpt={selectedCkpt}
      onSelectCkpt={(path) => { setSelectedCkpt(path); setResult(null); }}
      phaseFilter={phaseFilter}
      onTogglePhase={togglePhase}
      files={files}
      previews={previews}
      onAddFiles={addFiles}
      onRemoveFile={removeFile}
      onClearFiles={() => { setFiles([]); setResult(null); }}
      running={running}
      onRun={handleRun}
      medalMap={medalMap}
    />
  );

  const detail = (
    <Box sx={styles.detail}>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!result && !running && (
        <Box sx={styles.emptyState}>
          <Typography color="text.secondary">
            Select a checkpoint and upload image(s) to run inference.
          </Typography>
        </Box>
      )}

      {running && (
        <Box sx={styles.loadingState}>
          <CircularProgress />
          <Typography color="text.secondary">Running inference…</Typography>
        </Box>
      )}

      {result && !running && (
        <>
          {result.auto_cropped && (
            <Alert severity="info" icon={<CropIcon fontSize="small" />} sx={{ mb: 2 }}>
              Building automatically detected and cropped before inference.
            </Alert>
          )}

          {result.aggregated && <AggregatedPanel tasks={result.aggregated} />}

          <Typography variant="subtitle2" sx={styles.perImageLabel}>
            {result.per_image.length === 1 ? "Result" : `Per-image results (${result.per_image.length})`}
          </Typography>
          {activeCkpt && (
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mb: 1.5 }}>
              {[
                activeCkpt.backbone,
                `ph${activeCkpt.phase}`,
                `acc ${activeCkpt.best_overall_acc.toFixed(1)}%`,
                `lr ${activeCkpt.lr.toExponential(0)}`,
                activeCkpt.backbone_lr_scale != null ? `bb×${activeCkpt.backbone_lr_scale}` : "bb free",
                activeCkpt.scheduler,
                activeCkpt.freeze_phase1_heads ? "frozen" : "unfrozen",
                activeCkpt.input_type,
              ].map((p) => (
                <Chip key={p} label={p} size="small" variant="outlined" sx={{ fontSize: 10, height: 18 }} />
              ))}
            </Box>
          )}
          {result.per_image.map((img, i) => (
            <ImageResultPanel
              key={i}
              result={img}
              previewUrl={previews[i]}
              label={result.per_image.length > 1 ? `Image ${i + 1}: ${img.filename}` : img.filename}
              onImageClick={setLightboxSrc}
            />
          ))}
        </>
      )}

      <LightboxDialog src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
    </Box>
  );

  return <AppShell sidebar={sidebar} detail={detail} />;
}
