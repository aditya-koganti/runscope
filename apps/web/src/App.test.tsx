import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";

import { App } from "./App";

test("renders the RunScope foundation", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "RunScope" })).toBeInTheDocument();
});
