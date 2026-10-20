import { useState } from "react";

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked: the URL is still visible and selectable */
    }
  }

  return (
    <button type="button" className="btn btn-small" onClick={copy} aria-label={`Copy ${text}`}>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
