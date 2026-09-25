import { ShieldAlert, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type Confirmation = {
  title: string;
  message: string;
  confirmLabel?: string;
  risk?: string;
};

export function useConfirmation() {
  const [pending, setPending] = useState<Confirmation | null>(null);
  const resolver = useRef<((approved: boolean) => void) | null>(null);
  const cancelButton = useRef<HTMLButtonElement | null>(null);

  const finish = (approved: boolean) => {
    const resolve = resolver.current;
    resolver.current = null;
    setPending(null);
    resolve?.(approved);
  };

  useEffect(() => {
    if (!pending) return;
    cancelButton.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") finish(false);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [pending]);

  const request = (confirmation: Confirmation) => new Promise<boolean>((resolve) => {
    resolver.current?.(false);
    resolver.current = resolve;
    setPending(confirmation);
  });

  const dialog = pending ? (
    <div className="approval-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && finish(false)}>
      <section className="approval-dialog" role="alertdialog" aria-modal="true" aria-labelledby="approval-title" aria-describedby="approval-message">
        <header><span className="approval-icon"><ShieldAlert size={20} /></span><div><p className="eyebrow">Explicit approval required</p><h2 id="approval-title">{pending.title}</h2></div><button className="icon-button" type="button" aria-label="Close approval" onClick={() => finish(false)}><X size={17} /></button></header>
        <p id="approval-message">{pending.message}</p>
        {pending.risk && <div className="approval-risk"><strong>Risk</strong><span>{pending.risk}</span></div>}
        <footer><button ref={cancelButton} className="tool-button" type="button" onClick={() => finish(false)}>Cancel</button><button className="primary danger-action" type="button" onClick={() => finish(true)}>{pending.confirmLabel || "Continue"}</button></footer>
      </section>
    </div>
  ) : null;

  return { request, dialog };
}
