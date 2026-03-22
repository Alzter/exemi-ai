/**
 * postMessage into the bundled exemi-frontend iframe from a content script.
 *
 * Chromium and Firefox disagree on whether that iframe’s “origin” for
 * postMessage’s targetOrigin is the extension scheme or the embedder page.
 * Using a concrete origin throws in one browser or the other. The portable
 * approach is targetOrigin "*": delivery is still only to the given Window
 * reference (our iframe’s contentWindow), not a broadcast.
 */
function getExtensionRuntime(): { getURL: (path: string) => string } {
  const g = globalThis as typeof globalThis & {
    browser?: { runtime: { getURL: (path: string) => string } };
    chrome?: { runtime: { getURL: (path: string) => string } };
  };
  if (g.browser?.runtime?.getURL) return g.browser.runtime;
  if (g.chrome?.runtime?.getURL) return g.chrome.runtime;
  throw new Error("Extension runtime API not available");
}

export function getExtensionOrigin(): string {
  return new URL(getExtensionRuntime().getURL("")).origin;
}

/** Stable add-on id (hostname in moz-extension / chrome-extension URLs). */
export function getExtensionId(): string | undefined {
  const g = globalThis as typeof globalThis & {
    browser?: { runtime?: { id?: string } };
    chrome?: { runtime?: { id?: string } };
  };
  return g.browser?.runtime?.id ?? g.chrome?.runtime?.id;
}

/**
 * True if `origin` is this add-on’s extension origin. Firefox sometimes differs
 * from `getURL("").origin` string equality (normalization), so compare via runtime.id.
 */
export function extensionPostMessageOriginAllowed(
  origin: string,
  canonicalExtOrigin: string,
): boolean {
  if (origin === canonicalExtOrigin) return true;
  const id = getExtensionId();
  if (!id) return false;
  try {
    const u = new URL(origin);
    if (
      u.protocol !== "moz-extension:" &&
      u.protocol !== "chrome-extension:" &&
      u.protocol !== "safari-web-extension:"
    ) {
      return false;
    }
    return u.hostname === id;
  } catch {
    return false;
  }
}

/**
 * Accept EXEMI_AUTOMATION_READY from the bundled iframe. Prefer matching
 * event.source to iframe.contentWindow (Firefox-safe); fall back to origin checks.
 */
export function isTrustedIframeAutomationMessage(
  event: MessageEvent,
  iframeWindow: Window | null | undefined,
  canonicalExtOrigin: string,
): boolean {
  if (iframeWindow != null && event.source === iframeWindow) {
    return true;
  }
  return extensionPostMessageOriginAllowed(event.origin, canonicalExtOrigin);
}

export function postMessageToExemiIframe(
  iframeWin: Window | null | undefined,
  message: unknown,
): void {
  if (!iframeWin) return;
  if (iframeWin === window || iframeWin === window.top) return;

  iframeWin.postMessage(message, "*");
}
