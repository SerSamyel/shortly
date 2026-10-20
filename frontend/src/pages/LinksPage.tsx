import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import CopyButton from "../components/CopyButton";
import CreateLinkForm from "../components/CreateLinkForm";
import StatusBadge from "../components/StatusBadge";
import type { Link, LinkPage } from "../services";
import { ApiError } from "../services";
import { useSession } from "../session";

const PAGE_SIZE = 20;

export default function LinksPage() {
  const { api } = useSession();
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LinkPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<Link | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.listLinks(page, PAGE_SIZE));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load links");
    }
  }, [api, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function created(link: Link) {
    setJustCreated(link);
    if (page === 1) void load();
    else setPage(1);
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <h1>Your links</h1>
      <CreateLinkForm onCreated={created} />

      {justCreated && (
        <div className="card success" role="status">
          <span>Short link ready:</span>
          <a href={justCreated.short_url} target="_blank" rel="noreferrer" className="mono">
            {justCreated.short_url}
          </a>
          <CopyButton text={justCreated.short_url} />
        </div>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {data && data.total === 0 && <p className="empty muted">No links yet. Paste a URL above to create your first one.</p>}

      {data && data.total > 0 && (
        <ul className="link-list" aria-label="Links">
          {data.items.map((link) => (
            <li key={link.id} className="card link-row">
              <div className="link-main">
                <RouterLink to={`/app/links/${link.id}`} className="mono strong">
                  /{link.code}
                </RouterLink>
                <span className="target muted" title={link.target_url}>
                  {link.target_url}
                </span>
              </div>
              <div className="link-meta">
                <StatusBadge status={link.status} />
                <span className="clicks">
                  <strong>{link.total_clicks}</strong> {link.total_clicks === 1 ? "click" : "clicks"}
                </span>
                <CopyButton text={link.short_url} />
              </div>
            </li>
          ))}
        </ul>
      )}

      {pages > 1 && (
        <nav className="pager" aria-label="Pages">
          <button className="btn btn-small" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="muted small">
            Page {page} of {pages}
          </span>
          <button className="btn btn-small" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </nav>
      )}
    </>
  );
}
