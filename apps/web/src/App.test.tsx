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
