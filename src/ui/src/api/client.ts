import type {
  BuildingDetail,
  BuildingSummary,
  CheckpointInfo,
  DatasetInfo,
  EpochRecord,
  InferenceResponse,
  NeighborhoodStats,
  RunInfo,
} from "@/types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

async function postForm<T>(path: string, body: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listDatasets(): Promise<DatasetInfo[]> {
    return get("/datasets");
  },

  listNeighborhoods(dataset: string): Promise<NeighborhoodStats[]> {
    return get(`/datasets/${dataset}/neighborhoods`);
  },

  listBuildings(dataset: string, neighborhood: string): Promise<BuildingSummary[]> {
    return get(`/datasets/${dataset}/neighborhoods/${neighborhood}/buildings`);
  },

  searchBuildings(dataset: string, q: string, limit = 10): Promise<BuildingSummary[]> {
    return get(`/datasets/${dataset}/buildings/search?q=${encodeURIComponent(q)}&limit=${limit}`);
  },

  getBuilding(dataset: string, buildingId: string): Promise<BuildingDetail> {
    return get(`/datasets/${dataset}/buildings/${encodeURIComponent(buildingId)}`);
  },

  listRuns(): Promise<RunInfo[]> {
    return get("/runs");
  },

  getRunHistory(runId: string): Promise<EpochRecord[]> {
    return get(`/runs/${runId}/history`);
  },

  listCheckpoints(): Promise<CheckpointInfo[]> {
    return get("/checkpoints");
  },

  runInference(checkpointPath: string, images: File[]): Promise<InferenceResponse> {
    const form = new FormData();
    form.append("checkpoint_path", checkpointPath);
    for (const img of images) {
      form.append("images", img);
    }
    return postForm("/inference", form);
  },
};
