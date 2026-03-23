import type { ReactNode } from "react";

const DEFAULT_MESSAGE = "Exemi is loading, please wait…";

export type LoadingOverlayProps = {
  visible: boolean;
  /** Shown under the spinner; defaults to a generic configuring message. */
  message?: ReactNode;
};

/**
 * Covers the full viewport (Canvas and Exemi sidebar) while token automation runs.
 */
export function LoadingOverlay({ visible, message }: LoadingOverlayProps) {
  if (!visible) return null;

  return (
    <div
      className="exemi-loading-overlay"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="exemi-loading-overlay-backdrop" aria-hidden />
      <div className="exemi-loading-overlay-card">
        <div className="exemi-loading-spinner" aria-hidden />
        <p className="exemi-loading-overlay-text">{message ?? DEFAULT_MESSAGE}</p>
        <p className="exemi-loading-overlay-sub">
          Configuring the Exemi extension with your Canvas account.
        </p>
      </div>
    </div>
  );
}
