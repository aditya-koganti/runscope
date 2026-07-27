import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { App } from "./App";

function renderApp(route = "/overview") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

test("redirects a signed-out user to sign in", () => {
  renderApp();

  expect(screen.getByRole("heading", { name: "Sign in to RunScope" })).toBeInTheDocument();
});

test("signs in and renders the protected overview", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    if (String(input).endsWith("/auth/sign-in")) {
      return new Response(
        JSON.stringify({
          access_token: "test-token",
          token_type: "bearer",
          expires_in: 1800,
          user: {
            id: "019f9dc7-2f4c-7ec0-ac91-9652cd845c33",
            email: "researcher@runscope.dev",
            role: "researcher",
            created_at: "2026-07-26T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return new Response(JSON.stringify({ status: "ok", service: "api" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  const user = userEvent.setup();
  renderApp("/sign-in");

  await user.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
  expect(screen.getByText("researcher@runscope.dev")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalled();
});

test("shows a structured sign-in error", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        error: { code: "invalid_credentials", message: "Email or password is incorrect" },
      }),
      { status: 401, headers: { "Content-Type": "application/json" } },
    ),
  );
  const user = userEvent.setup();
  renderApp("/sign-in");

  await user.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Email or password is incorrect",
  );
});

test("sign out returns to the sign-in page", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        access_token: "test-token",
        token_type: "bearer",
        expires_in: 1800,
        user: {
          id: "019f9dc7-2f4c-7ec0-ac91-9652cd845c33",
          email: "researcher@runscope.dev",
          role: "researcher",
          created_at: "2026-07-26T00:00:00Z",
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );
  const user = userEvent.setup();
  renderApp("/sign-in");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByRole("heading", { name: "Overview" });

  await user.click(screen.getByRole("button", { name: "Sign out" }));

  expect(screen.getByRole("heading", { name: "Sign in to RunScope" })).toBeInTheDocument();
});

test("creates a project through the protected form", async () => {
  let created = false;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith("/auth/sign-in")) {
      return new Response(
        JSON.stringify({
          access_token: "test-token",
          token_type: "bearer",
          expires_in: 1800,
          user: {
            id: "019f9dc7-2f4c-7ec0-ac91-9652cd845c33",
            email: "researcher@runscope.dev",
            role: "researcher",
            created_at: "2026-07-26T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.includes("/projects") && init?.method === "POST") {
      created = true;
      return new Response(
        JSON.stringify({
          id: "019f9dc7-2f4c-7ec0-ac91-9652cd845c34",
          name: "Forecasting",
          description: "Demand models",
          created_by: "019f9dc7-2f4c-7ec0-ac91-9652cd845c33",
          created_at: "2026-07-26T00:00:00Z",
          updated_at: "2026-07-26T00:00:00Z",
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.includes("/projects?")) {
      return new Response(
        JSON.stringify({
          items: created
            ? [
                {
                  id: "019f9dc7-2f4c-7ec0-ac91-9652cd845c34",
                  name: "Forecasting",
                  description: "Demand models",
                  created_by: "019f9dc7-2f4c-7ec0-ac91-9652cd845c33",
                  created_at: "2026-07-26T00:00:00Z",
                  updated_at: "2026-07-26T00:00:00Z",
                },
              ]
            : [],
          page: 1,
          page_size: 20,
          total: created ? 1 : 0,
          pages: created ? 1 : 0,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return new Response(JSON.stringify({ status: "ok", service: "api" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  const user = userEvent.setup();
  renderApp("/sign-in");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByRole("heading", { name: "Overview" });

  await user.click(screen.getByRole("link", { name: "Projects" }));
  expect(await screen.findByRole("heading", { name: "No projects yet" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "New project" }));
  await user.type(screen.getByLabelText("Project name"), "Forecasting");
  await user.type(screen.getByLabelText("Description"), "Demand models");
  await user.click(screen.getByRole("button", { name: "Create project" }));

  expect(await screen.findByRole("link", { name: "Forecasting" })).toBeInTheDocument();
});

test("renders dependency and backlog health for an authenticated viewer", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/auth/sign-in")) {
      return new Response(
        JSON.stringify({
          access_token: "test-token",
          token_type: "bearer",
          expires_in: 1800,
          user: {
            id: "019f9dc7-2f4c-7ec0-ac91-9652cd845c33",
            email: "viewer@runscope.dev",
            role: "viewer",
            created_at: "2026-07-26T00:00:00Z",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.endsWith("/platform/dependencies")) {
      return new Response(
        JSON.stringify({
          status: "healthy",
          dependencies: {
            api: { status: "healthy", latency_ms: 0 },
            postgresql: { status: "healthy", latency_ms: 1.25 },
            scheduler: { status: "healthy", latency_ms: 2.5 },
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.endsWith("/platform/summary")) {
      return new Response(
        JSON.stringify({
          active_runs: 1,
          queued_runs: 2,
          failed_runs: 0,
          successful_runs: 3,
          success_rate: 1,
          average_duration_seconds: 4.2,
          workers_online: 2,
          workers_total: 2,
          available_cpu: 6,
          total_cpu: 8,
          available_memory_mb: 12288,
          total_memory_mb: 16384,
          queue_depth: 2,
          unpublished_messages: 1,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.includes("/runs?")) {
      return new Response(
        JSON.stringify({ items: [], page: 1, page_size: 8, total: 0, pages: 0 }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return new Response(JSON.stringify({ status: "ok", service: "api" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  const user = userEvent.setup();
  renderApp("/sign-in");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByRole("heading", { name: "Overview" });

  await user.click(screen.getByRole("link", { name: "Platform health" }));

  expect(await screen.findByRole("heading", { name: "Platform health" })).toBeInTheDocument();
  expect(screen.getByText("scheduler", { exact: true })).toBeInTheDocument();
  expect(screen.getByText("2.50 ms probe latency")).toBeInTheDocument();
  expect(screen.getByText("awaiting Redpanda")).toBeInTheDocument();
});
