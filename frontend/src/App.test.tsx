import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { createMockApi } from "./services/mock";
import { memoryTokens, renderApp } from "./test-utils";

async function signUp(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Email"), "owner@example.com");
  await user.type(screen.getByLabelText("Password"), "long-enough");
  await user.click(screen.getByRole("button", { name: "Sign up" }));
  await screen.findByRole("heading", { name: "Your links" });
}

describe("authentication", () => {
  it("sends an anonymous visitor to the login page", async () => {
    renderApp("/app");
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("signs up and lands on an empty links page", async () => {
    const user = userEvent.setup();
    renderApp("/signup");
    await signUp(user);
    // The list loads after the page renders, so wait for the empty state.
    expect(await screen.findByText(/No links yet/)).toBeInTheDocument();
  });

  it("shows the server's message for wrong credentials", async () => {
    const user = userEvent.setup();
    renderApp("/login");
    await user.type(screen.getByLabelText("Email"), "nobody@example.com");
    await user.type(screen.getByLabelText("Password"), "whatever-123");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong email or password");
  });

  it("shows a field error for a short password", async () => {
    const user = userEvent.setup();
    renderApp("/signup");
    await user.type(screen.getByLabelText("Email"), "a@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Sign up" }));
    expect(await screen.findByText(/at least 8 characters/)).toBeInTheDocument();
  });

  it("logs out", async () => {
    const user = userEvent.setup();
    renderApp("/signup");
    await signUp(user);
    await user.click(screen.getByRole("button", { name: "Log out" }));
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });
});

describe("links", () => {
  it("creates a link with an alias and lists it", async () => {
    const user = userEvent.setup();
    renderApp("/signup");
    await signUp(user);

    await user.type(screen.getByPlaceholderText(/Paste a long URL/), "https://example.com/very/long");
    await user.click(screen.getByRole("button", { name: /Custom alias/ }));
    await user.type(screen.getByLabelText("Custom alias"), "my-talk");
    await user.click(screen.getByRole("button", { name: "Shorten" }));

    expect(await screen.findByRole("status")).toHaveTextContent("http://localhost:8000/my-talk");
    const list = await screen.findByRole("list", { name: "Links" });
    expect(within(list).getByText("/my-talk")).toBeInTheDocument();
    expect(within(list).getByText("Active")).toBeInTheDocument();
  });

  it("shows the alias error next to the form", async () => {
    const user = userEvent.setup();
    renderApp("/signup");
    await signUp(user);
    await user.type(screen.getByPlaceholderText(/Paste a long URL/), "https://example.com");
    await user.click(screen.getByRole("button", { name: /Custom alias/ }));
    await user.type(screen.getByLabelText("Custom alias"), "api");
    await user.click(screen.getByRole("button", { name: "Shorten" }));
    expect(await screen.findByText("Alias 'api' is reserved")).toBeInTheDocument();
  });

  it("opens analytics, disables and deletes a link", async () => {
    const user = userEvent.setup();
    const tokens = memoryTokens();
    const api = createMockApi(tokens, { seed: true });
    tokens.set((await api.login("demo@example.com", "demo-password")).access_token);
    renderApp("/app", api, tokens);

    await user.click(await screen.findByRole("link", { name: "/demo-talk" }));
    expect(await screen.findByRole("img", { name: "Clicks per day" })).toBeInTheDocument();
    expect(screen.getByText("t.me")).toBeInTheDocument();
    expect(screen.getByText("57")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Disable" }));
    expect(await screen.findByText("Disabled")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Yes, delete" }));
    await screen.findByRole("heading", { name: "Your links" });
    await waitFor(() => expect(screen.getByText(/No links yet/)).toBeInTheDocument());
  });
});
