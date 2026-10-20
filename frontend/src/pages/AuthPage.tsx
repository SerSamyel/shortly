import { useState } from "react";
import type { FormEvent } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { ApiError } from "../services";
import { useSession } from "../session";

export default function AuthPage({ mode }: { mode: "login" | "signup" }) {
  const { signIn } = useSession();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password, mode);
      navigate("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "Something went wrong"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth card">
      <h1>{isLogin ? "Log in" : "Create an account"}</h1>
      <p className="muted">Short links for your talks, posts and chats, with click analytics.</p>
      <form onSubmit={submit} noValidate>
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        {error?.fieldError("email") && <p className="field-error">{error.fieldError("email")}</p>}
        <label>
          Password
          <input
            type="password"
            autoComplete={isLogin ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        {error?.fieldError("password") && <p className="field-error">{error.fieldError("password")}</p>}
        {error && error.errors.length === 0 && (
          <p className="form-error" role="alert">
            {error.detail}
          </p>
        )}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Please wait…" : isLogin ? "Log in" : "Sign up"}
        </button>
      </form>
      <p className="muted small">
        {isLogin ? (
          <>
            No account yet? <RouterLink to="/signup">Sign up</RouterLink>
          </>
        ) : (
          <>
            Already registered? <RouterLink to="/login">Log in</RouterLink>
          </>
        )}
      </p>
    </section>
  );
}
