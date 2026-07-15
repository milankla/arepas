import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import App from "@/App";

const authState = vi.hoisted(() => ({
  authEnabled: true,
  isAuthenticated: false,
  isLoading: false,
}));

vi.mock("@/auth/config", () => ({
  get AUTH_ENABLED() {
    return authState.authEnabled;
  },
}));

vi.mock("react-oidc-context", () => ({
  useAuth: () => ({
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    signinRedirect: vi.fn(),
    signoutRedirect: vi.fn(),
    user: null,
  }),
}));

vi.mock("@/components/layout/TopBar", () => ({
  TopBar: () => <div data-testid="top-bar" />,
}));

vi.mock("@/auth/AuthSync", () => ({
  AuthSync: () => null,
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
    authState.authEnabled = true;
    authState.isAuthenticated = false;
    authState.isLoading = false;

    renderAtRoot();

    expect(await screen.findByText("Inference page")).toBeInTheDocument();
    expect(screen.queryByText("Explore page")).not.toBeInTheDocument();
  });

  it("keeps authenticated users on Explore at /", () => {
    authState.authEnabled = true;
    authState.isAuthenticated = true;
    authState.isLoading = false;

    renderAtRoot();

    expect(screen.getByText("Explore page")).toBeInTheDocument();
    expect(screen.queryByText("Inference page")).not.toBeInTheDocument();
  });

  it("keeps auth-disabled local mode on Explore at /", () => {
    authState.authEnabled = false;
    authState.isAuthenticated = false;
    authState.isLoading = false;

    renderAtRoot();

    expect(screen.getByText("Explore page")).toBeInTheDocument();
    expect(screen.queryByText("Inference page")).not.toBeInTheDocument();
  });
});