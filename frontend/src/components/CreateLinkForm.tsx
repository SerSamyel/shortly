import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "../services";
import type { Link } from "../services";
import { useSession } from "../session";

export default function CreateLinkForm({ onCreated }: { onCreated: (link: Link) => void }) {
  const { api } = useSession();
  const [targetUrl, setTargetUrl] = useState("");
  const [alias, setAlias] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [showOptions, setShowOptions] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const link = await api.createLink({
        target_url: targetUrl.trim(),
        alias: alias.trim() || null,
        // <input type="datetime-local"> is local time; the API wants an absolute instant.
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      });
      setTargetUrl("");
      setAlias("");
      setExpiresAt("");
      onCreated(link);
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, "Something went wrong"));
    } finally {
      setBusy(false);
    }
  }

  const fieldError = (field: string) => error?.fieldError(field);

  return (
    <form className="card create-form" onSubmit={submit} noValidate aria-label="Create a short link">
      <div className="create-row">
        <label className="grow">
          <span className="sr-only">Long URL</span>
          <input
            type="url"
            placeholder="Paste a long URL, e.g. https://example.com/very/long/page"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            required
          />
        </label>
        <button className="btn btn-primary" type="submit" disabled={busy || !targetUrl.trim()}>
          {busy ? "Shortening…" : "Shorten"}
        </button>
      </div>
      {fieldError("target_url") && <p className="field-error">{fieldError("target_url")}</p>}

      <button type="button" className="link-button small" onClick={() => setShowOptions((v) => !v)}>
        {showOptions ? "Hide options" : "Custom alias or expiration"}
      </button>

      {showOptions && (
        <div className="options">
          <label>
            Custom alias
            <input
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="my-talk"
              maxLength={32}
            />
          </label>
          <label>
            Expires at
            <input type="datetime-local" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
          </label>
        </div>
      )}
      {fieldError("alias") && <p className="field-error">{fieldError("alias")}</p>}
      {fieldError("expires_at") && <p className="field-error">{fieldError("expires_at")}</p>}
      {error && error.errors.length === 0 && (
        <p className="form-error" role="alert">
          {error.detail}
        </p>
      )}
    </form>
  );
}
