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

export function postMessageToExemiIframe(
  iframeWin: Window | null | undefined,
  message: unknown,
): void {
  if (!iframeWin) return;
  if (iframeWin === window || iframeWin === window.top) return;

  iframeWin.postMessage(message, "*");
}
