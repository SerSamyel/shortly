import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { createMockApi } from "./services/mock";
import type { Api, TokenStore } from "./services";
import { SessionProvider } from "./session";

export function memoryTokens(): TokenStore {
  let token: string | null = null;
  return { get: () => token, set: (t) => void (token = t) };
}

export function renderApp(path = "/", api?: Api, tokens: TokenStore = memoryTokens()) {
  const backend = api ?? createMockApi(tokens);
  const utils = render(
    <MemoryRouter initialEntries={[path]}>
      <SessionProvider api={backend} tokens={tokens}>
        <App />
      </SessionProvider>
    </MemoryRouter>,
  );
  return { ...utils, api: backend, tokens };
}
