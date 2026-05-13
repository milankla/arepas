import { Box, Chip, Grid, Paper, Typography } from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { NeighborhoodStats } from "@/types";

// Human-readable labels for each attribute column
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

interface NeighborhoodPanelProps {
  stats: NeighborhoodStats;
}

export function NeighborhoodPanel({ stats }: NeighborhoodPanelProps) {
  return (
    <Box>
      {/* Header */}
      <Typography variant="h5" sx={{ fontWeight: 700 }} gutterBottom>
        {stats.neighborhood}
      </Typography>
      <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
        <Chip label={`${stats.building_count} buildings`} color="primary" variant="outlined" />
        <Chip label={`${stats.image_count} images`} color="secondary" variant="outlined" />
      </Box>

      {/* Attribute frequency charts */}
      <Grid container spacing={2}>
        {stats.attribute_frequencies.map((freq) => {
          const data = Object.entries(freq.counts)
            .map(([name, count]) => ({ name, count }))
            .sort((a, b) => b.count - a.count);

          if (data.length === 0) return null;

          return (
            <Grid key={freq.attribute} size={{ xs: 12, sm: 6, lg: 4 }}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }} gutterBottom>
                  {ATTRIBUTE_LABELS[freq.attribute] ?? freq.attribute}
                </Typography>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={110}
                      tick={{ fontSize: 10 }}
                      tickFormatter={(v: string) =>
                        v.length > 16 ? `${v.slice(0, 15)}…` : v
                      }
                    />
                    <Tooltip
                      formatter={(value) => [value ?? 0, "count"]}
                      labelStyle={{ fontWeight: 600 }}
                    />
                    <Bar dataKey="count" fill="#1976d2" radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
}
