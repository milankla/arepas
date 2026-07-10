import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DatasetProvider, useDataset } from "@/context/DatasetContext";

vi.mock("@/auth/config", () => ({ AUTH_ENABLED: true }));

let mockAuthState = {
  isLoading: true,
  isAuthenticated: false,
  user: null as { id_token?: string } | null,
};

vi.mock("react-oidc-context", () => ({
  useAuth: () => mockAuthState,
}));

const MOCK_DATASETS = [
  { id: "data2", label: "data2", building_count: 759, image_count: 2708, neighborhoods: ["Cole"] },
];

function Probe() {
  const { datasets, activeDataset, loading, error } = useDataset();
  return (
    <div>
      <span data-testid="count">{datasets.length}</span>
      <span data-testid="active">{activeDataset}</span>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="error">{error ?? ""}</span>
    </div>
  );
}

describe("DatasetProvider auth gating", () => {
  beforeEach(() => {
    mockAuthState = { isLoading: true, isAuthenticated: false, user: null };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(MOCK_DATASETS),
      })
    );
  });

  it("waits for a Cognito session before loading protected datasets", async () => {
    const { rerender } = render(
      <DatasetProvider>
        <Probe />
      </DatasetProvider>
    );

    expect(fetch).not.toHaveBeenCalled();
    expect(screen.getByTestId("loading")).toHaveTextContent("true");

    mockAuthState = {
      isLoading: false,
      isAuthenticated: true,
      user: { id_token: "id-token" },
    };

    rerender(
      <DatasetProvider>
        <Probe />
      </DatasetProvider>
    );

    await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/datasets", { headers: { Authorization: "Bearer id-token" } }));
    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("1"));
    expect(screen.getByTestId("active")).toHaveTextContent("data2");
    expect(screen.getByTestId("error")).toHaveTextContent("");
  });
});