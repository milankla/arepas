import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeAll, describe, expect, it, vi } from "vitest";

let TopBar: typeof import("@/components/layout/TopBar").TopBar;

const mockSigninRedirect = vi.fn();

beforeAll(async () => {
  vi.resetModules();
  vi.doMock("@/auth/config", () => ({ AUTH_ENABLED: true }));
  vi.doMock("react-oidc-context", () => ({
    useAuth: () => ({
      isAuthenticated: false,
      signinRedirect: mockSigninRedirect,
      signoutRedirect: vi.fn(),
      user: null,
    }),
  }));
  vi.doMock("@/context/DatasetContext", () => ({
    useDataset: () => ({
      datasets: [{ id: "data2", label: "data2", building_count: 759 }],
      activeDataset: "data2",
      setActiveDataset: vi.fn(),
      loading: false,
    }),
  }));
  vi.doMock("@/context/SearchContext", () => ({
    useSearch: () => ({ selectBuilding: vi.fn() }),
  }));
  vi.doMock("@/api/client", () => ({
    api: { searchBuildings: vi.fn().mockResolvedValue([]) },
  }));
  TopBar = (await import("@/components/layout/TopBar")).TopBar;
});

describe("TopBar anonymous state", () => {
  it("hides Explore, Training, and dataset selector while keeping sign in visible", () => {
    render(
      <MemoryRouter initialEntries={["/inference"]}>
        <TopBar />
      </MemoryRouter>
    );

    expect(screen.queryByRole("tab", { name: "Explore" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Training" })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Inference" })).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });
});