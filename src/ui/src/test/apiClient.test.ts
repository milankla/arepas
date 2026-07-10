import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, setAuthToken } from "@/api/client";
import type { DatasetInfo } from "@/types";

const MOCK_DATASETS: DatasetInfo[] = [
  { id: "data2", label: "data2", building_count: 759, image_count: 2708, neighborhoods: ["Cole", "Regis"] },
];

describe("api.listDatasets", () => {
  beforeEach(() => {
    setAuthToken(null);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_DATASETS),
      })
    );
  });

  it("calls /api/datasets and returns dataset list", async () => {
    const result = await api.listDatasets();
    expect(fetch).toHaveBeenCalledWith("/api/datasets", { headers: {} });
    expect(result).toEqual(MOCK_DATASETS);
  });

  it("includes the ID token when one is set", async () => {
    setAuthToken("id-token");
    await api.listDatasets();
    expect(fetch).toHaveBeenCalledWith("/api/datasets", { headers: { Authorization: "Bearer id-token" } });
  });
});

describe("api.listDatasets — error handling", () => {
  beforeEach(() => {
    setAuthToken(null);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        text: () => Promise.resolve("Not found"),
      })
    );
  });

  it("throws when the API returns a non-ok status", async () => {
    await expect(api.listDatasets()).rejects.toThrow("API 404");
  });
});
