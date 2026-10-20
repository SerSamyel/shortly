import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Api, TokenStore, User } from "./services";

interface Session {
  api: Api;
  user: User | null;
  loading: boolean;
  signIn(email: string, password: string, mode: "login" | "signup"): Promise<void>;
  signOut(): void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({
  api,
  tokens,
  children,
}: {
  api: Api;
  tokens: TokenStore;
  children: ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => tokens.get() !== null);

  useEffect(() => {
    if (!tokens.get()) return;
    let cancelled = false;
    api
      .me()
      .then((u) => !cancelled && setUser(u))
      .catch(() => tokens.set(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [api, tokens]);

  const signIn = useCallback(
    async (email: string, password: string, mode: "login" | "signup") => {
      const result = mode === "login" ? await api.login(email, password) : await api.signup(email, password);
      tokens.set(result.access_token);
      setUser(result.user);
    },
    [api, tokens],
  );

  const signOut = useCallback(() => {
    tokens.set(null);
    setUser(null);
  }, [tokens]);

  const value = useMemo(() => ({ api, user, loading, signIn, signOut }), [api, user, loading, signIn, signOut]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside SessionProvider");
  return session;
}
