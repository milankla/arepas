export const TASK_LABELS: Record<string, string> = {
  // Phase 1 & 2 tasks
  stories: "Stories",
  roof_type: "Roof Type",
  primary_cladding: "Primary Cladding",
  chimney_present: "Chimney Present",
  setting: "Setting",
  alteration_level: "Alteration Level",
  architectural_style: "Architectural Style",
  building_form: "Building Form",
  
  // Phase 3 tasks (fine-grained architectural attributes)
  wall_features: "Wall Features",
  landscape_features: "Landscape Features",
  window: "Window",
  entrance: "Entrance",
  associated_buildings: "Associated Buildings",
  building_category: "Building Category",
  roof_materials: "Roof Materials",
};

export const PHASE3_TASKS = new Set([
  "wall_features",
  "landscape_features",
  "window",
  "entrance",
  "associated_buildings",
  "building_category",
  "roof_materials",
]);

export function taskLabel(task: string): string {
  return TASK_LABELS[task] ?? task.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
