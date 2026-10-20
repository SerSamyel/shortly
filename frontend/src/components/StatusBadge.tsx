import type { LinkStatus } from "../services";

const LABELS: Record<LinkStatus, string> = { active: "Active", disabled: "Disabled", expired: "Expired" };

export default function StatusBadge({ status }: { status: LinkStatus }) {
  return <span className={`badge badge-${status}`}>{LABELS[status]}</span>;
}
