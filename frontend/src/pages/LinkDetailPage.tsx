import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import ClicksChart from "../components/ClicksChart";
import CopyButton from "../components/CopyButton";
import StatusBadge from "../components/StatusBadge";
import type { Link, LinkStats, NamedCount } from "../services";
import { ApiError } from "../services";
import { useSession } from "../session";

function TopList({ title, items, empty }: { title: string; items: NamedCount[]; empty: string }) {
  const max = Math.max(1, ...items.map((i) => i.clicks));
  return (
    <section className="card">
      <h2>{title}</h2>
      {items.length === 0 ? (
        <p className="muted small">{empty}</p>
      ) : (
        <ol className="top-list">
          {items.map((item) => (
            <li key={item.name}>
              <span className="top-name">{item.name}</span>
              <span className="top-bar" style={{ width: `${(item.clicks / max) * 100}%` }} />
              <span className="top-count">{item.clicks}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function LinkDetailPage() {
  const { id } = useParams();
  const linkId = Number(id);
  const { api } = useSession();
  const navigate = useNavigate();
  const [link, setLink] = useState<Link | null>(null);
  const [stats, setStats] = useState<LinkStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [l, s] = await Promise.all([api.getLink(linkId), api.getStats(linkId, 30)]);
      setLink(l);
      setStats(s);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load this link");
    }
  }, [api, linkId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggle() {
    if (!link) return;
    setBusy(true);
    try {
      setLink(await api.setLinkActive(link.id, !link.is_active));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update the link");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!link) return;
    setBusy(true);
    try {
      await api.deleteLink(link.id);
      navigate("/app");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete the link");
      setBusy(false);
    }
  }

  if (error && !link) {
    return (
      <>
        <p className="form-error" role="alert">
          {error}
        </p>
        <RouterLink to="/app">Back to links</RouterLink>
      </>
    );
  }
  if (!link || !stats) return <p className="muted center">Loading…</p>;

  const last7 = stats.daily.slice(-7).reduce((sum, d) => sum + d.clicks, 0);

  return (
    <>
      <RouterLink to="/app" className="small">
        ← All links
      </RouterLink>
      <header className="detail-head">
        <div>
          <h1 className="mono">/{link.code}</h1>
          <p className="target muted" title={link.target_url}>
            → {link.target_url}
          </p>
        </div>
        <StatusBadge status={link.status} />
      </header>

      <div className="card detail-actions">
        <a href={link.short_url} target="_blank" rel="noreferrer" className="mono">
          {link.short_url}
        </a>
        <CopyButton text={link.short_url} />
        <span className="spacer" />
        <button type="button" className="btn btn-small" onClick={toggle} disabled={busy}>
          {link.is_active ? "Disable" : "Enable"}
        </button>
        {confirmDelete ? (
          <>
            <span className="small">Delete link and its analytics?</span>
            <button type="button" className="btn btn-small btn-danger" onClick={remove} disabled={busy}>
              Yes, delete
            </button>
            <button type="button" className="btn btn-small btn-ghost" onClick={() => setConfirmDelete(false)}>
              Cancel
            </button>
          </>
        ) : (
          <button type="button" className="btn btn-small btn-ghost" onClick={() => setConfirmDelete(true)}>
            Delete
          </button>
        )}
      </div>
      {link.expires_at && (
        <p className="muted small">
          {link.status === "expired" ? "Expired" : "Expires"} {new Date(link.expires_at).toLocaleString()}
        </p>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <section className="kpis">
        <div className="card kpi">
          <span className="kpi-value">{stats.total_clicks}</span>
          <span className="muted small">Total clicks</span>
        </div>
        <div className="card kpi">
          <span className="kpi-value">{last7}</span>
          <span className="muted small">Last 7 days</span>
        </div>
        <div className="card kpi">
          <span className="kpi-value">{stats.daily.at(-1)?.unique_visitors ?? 0}</span>
          <span className="muted small">Unique visitors today</span>
        </div>
      </section>

      <section className="card">
        <h2>Clicks, last 30 days</h2>
        <ClicksChart daily={stats.daily} />
        <p className="muted small">Clicks appear here within a minute.</p>
      </section>

      <div className="two-col">
        <TopList title="Top referrers" items={stats.referrers} empty="No clicks yet." />
        <TopList title="Top countries" items={stats.countries} empty="No clicks yet." />
      </div>
    </>
  );
}
