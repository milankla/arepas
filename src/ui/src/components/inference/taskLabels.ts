export const TASK_LABELS: Record<string, string> = {
  stories: "Stories",
  roof_type: "Roof Type",
  primary_cladding: "Primary Cladding",
  chimney_present: "Chimney Present",
  setting: "Setting",
  alteration_level: "Alteration Level",
  architectural_style: "Architectural Style",
  building_form: "Building Form",
};

export function taskLabel(task: string): string {
  return TASK_LABELS[task] ?? task.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
