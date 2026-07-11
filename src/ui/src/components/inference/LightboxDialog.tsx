import { Box, Dialog, DialogContent, IconButton } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

const styles = {
  paper: {
    bgcolor: "transparent",
    boxShadow: "none",
  },
  content: {
    p: 0,
    position: "relative",
    lineHeight: 0,
  },
  closeBtn: {
    position: "absolute",
    top: 8,
    right: 8,
    bgcolor: "rgba(0,0,0,0.55)",
    color: "white",
    "&:hover": { bgcolor: "rgba(0,0,0,0.75)" },
    zIndex: 1,
  },
  img: {
    display: "block",
    maxHeight: "90vh",
    maxWidth: "90vw",
    borderRadius: 1,
  },
} as const;

export function LightboxDialog({ src, onClose }: { src: string | null; onClose: () => void }) {
  return (
    <Dialog
      open={!!src}
      onClose={onClose}
      maxWidth={false}
      slotProps={{ paper: { sx: styles.paper } }}
    >
      <DialogContent sx={styles.content}>
        <IconButton onClick={onClose} size="small" sx={styles.closeBtn}>
          <CloseIcon fontSize="small" />
        </IconButton>
        {src && <Box component="img" src={src} sx={styles.img} />}
      </DialogContent>
    </Dialog>
  );
}
