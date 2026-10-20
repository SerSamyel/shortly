import { Link as RouterLink, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { useSession } from "./session";
import AuthPage from "./pages/AuthPage";
import LinksPage from "./pages/LinksPage";
import LinkDetailPage from "./pages/LinkDetailPage";

function RequireUser({ children }: { children: ReactNode }) {
  const { user, loading } = useSession();
  if (loading) return <p className="muted center">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Header() {
  const { user, signOut } = useSession();
  return (
    <header className="topbar">
      <RouterLink to={user ? "/app" : "/"} className="brand">
        <span className="brand-mark" aria-hidden="true" />
        Shortly
      </RouterLink>
      {user && (
        <div className="topbar-user">
          <span className="muted">{user.email}</span>
          <button type="button" className="btn btn-ghost" onClick={signOut}>
            Log out
          </button>
        </div>
      )}
    </header>
  );
}

export default function App() {
  const { user, loading } = useSession();
  return (
    <>
      <Header />
      <main className="container">
        <Routes>
          <Route path="/" element={loading ? null : <Navigate to={user ? "/app" : "/login"} replace />} />
          <Route path="/login" element={user ? <Navigate to="/app" replace /> : <AuthPage mode="login" />} />
          <Route path="/signup" element={user ? <Navigate to="/app" replace /> : <AuthPage mode="signup" />} />
          <Route
            path="/app"
            element={
              <RequireUser>
                <LinksPage />
              </RequireUser>
            }
          />
          <Route
            path="/app/links/:id"
            element={
              <RequireUser>
                <LinkDetailPage />
              </RequireUser>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
