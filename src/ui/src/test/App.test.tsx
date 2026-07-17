import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "@/App";

// Control the role returned by useUserRole across test cases
const roleState = vi.hoisted(() => ({ value: "anonymous" as string }));

vi.mock("@/auth/useUserRole", () => ({
  useUserRole: () => roleState.value,
}));

vi.mock("@/components/layout/TopBar", () => ({
  TopBar: () => <div data-testid="top-bar" />,
}));

vi.mock("@/auth/AuthSync", () => ({
  AuthSync: () => null,
}));

vi.mock("@/auth/RequireAuth", () => ({
  RequireAuth: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/pages/ExploreDataPage", () => ({
  default: () => <div>Explore page</div>,
}));

vi.mock("@/pages/InferencePage", () => ({
  default: () => <div>Inference page</div>,
}));

vi.mock("@/pages/TrainingEvaluationPage", () => ({
  default: () => <div>Training page</div>,
}));

function renderAtRoot() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>
  );
}

describe("App home route", () => {
  it("redirects anonymous users from / to /inference", async () => {
    roleState.value = "anonymous";
    renderAtRoot();
    expect(await screen.findByText("Inference page")).toBeInTheDocument();
    expect(screen.queryByText("Explore page")).not.toBeInTheDocument();
  });

  it("keeps user role on Explore at /", () => {
    roleState.value = "user";
    renderAtRoot();
    expect(screen.getByText("Explore page")).toBeInTheDocument();
    expect(screen.queryByText("Inference page")).not.toBeInTheDocument();
  });

  it("keeps admin role on Explore at /", () => {
    roleState.value = "admin";
    renderAtRoot();
    expect(screen.getByText("Explore page")).toBeInTheDocument();
    expect(screen.queryByText("Inference page")).not.toBeInTheDocument();
  });

  it("redirects user role from /training to /", () => {
    roleState.value = "user";
    render(
      <MemoryRouter initialEntries={["/training"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText("Explore page")).toBeInTheDocument();
    expect(screen.queryByText("Training page")).not.toBeInTheDocument();
  });

  it("allows admin role on /training", () => {
    roleState.value = "admin";
    render(
      <MemoryRouter initialEntries={["/training"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText("Training page")).toBeInTheDocument();
  });
});