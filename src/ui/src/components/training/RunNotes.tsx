import { Box, Divider, Typography } from "@mui/material";
import type { RunNotes as RunNotesType } from "@/types";

interface RunNotesProps {
  runId: string;
  notes: RunNotesType;
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="caption" color="text.disabled" sx={{ fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
        {title}
      </Typography>
      <Box component="ul" sx={{ m: 0, mt: 0.5, pl: 2.5 }}>
        {items.map((item, i) => (
          <Box component="li" key={i} sx={{ mb: 0.25 }}>
            <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
              {item}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export function RunNotes({ notes }: RunNotesProps) {
  return (
    <Box sx={{ mt: 3 }}>
      <Divider sx={{ mb: 2 }} />
      <Typography variant="caption" color="text.disabled" sx={{ fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
        Notes
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2, lineHeight: 1.6 }}>
        {notes.summary}
      </Typography>
      <Section title="Learnings" items={notes.learnings} />
      <Section title="Next Steps" items={notes.next_steps} />
    </Box>
  );
}

