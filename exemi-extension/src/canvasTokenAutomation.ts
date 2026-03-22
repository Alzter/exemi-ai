import {
  CANVAS_TOKEN_AUTOMATION_SS_KEY,
  EXEMI_AUTOMATION_READY,
  EXEMI_AUTOMATION_REDIRECTING,
  EXEMI_CANVAS_TOKEN_RESULT,
  type CanvasTokenAutomationState,
  type ExemiAutomationReadyPayload,
  type ExemiCanvasTokenResultPayload,
} from "./extensionAutomationMessages";

function getExpiryDays(): number {
  const raw = import.meta.env.VITE_CANVAS_TOKEN_EXPIRY_DAYS;
  const n = raw != null && raw !== "" ? Number(raw) : 30;
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 30;
}

function expiryDateYyyyMmDd(): string {
  const d = new Date();
  d.setDate(d.getDate() + getExpiryDays());
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function getExtensionRuntime(): { getURL: (path: string) => string } {
  const g = globalThis as typeof globalThis & {
    browser?: { runtime: { getURL: (path: string) => string } };
    chrome?: { runtime: { getURL: (path: string) => string } };
  };
  if (g.browser?.runtime?.getURL) return g.browser.runtime;
  if (g.chrome?.runtime?.getURL) return g.chrome.runtime;
  throw new Error("Extension runtime API not available");
}

function extensionOrigin(): string {
  return new URL(getExtensionRuntime().getURL("")).origin;
}

function isExtensionIframeOrigin(origin: string): boolean {
  try {
    const u = new URL(origin);
    return (
      u.protocol === "chrome-extension:" ||
      u.protocol === "moz-extension:" ||
      u.protocol === "safari-web-extension:"
    );
  } catch {
    return false;
  }
}

function readAutomationState(): CanvasTokenAutomationState | null {
  try {
    const raw = sessionStorage.getItem(CANVAS_TOKEN_AUTOMATION_SS_KEY);
    if (!raw) return null;
    const o = JSON.parse(raw) as CanvasTokenAutomationState;
    if (!o || typeof o.phase !== "string") return null;
    return o;
  } catch {
    return null;
  }
}

function writeAutomationState(phase: CanvasTokenAutomationState["phase"]) {
  const s: CanvasTokenAutomationState = { phase, ts: Date.now() };
  try {
    sessionStorage.setItem(CANVAS_TOKEN_AUTOMATION_SS_KEY, JSON.stringify(s));
  } catch {
    // ignore
  }
}

function clearAutomationState() {
  try {
    sessionStorage.removeItem(CANVAS_TOKEN_AUTOMATION_SS_KEY);
  } catch {
    // ignore
  }
}

function canvasUniversitySubdomain(host: string): string | undefined {
  if (!host.endsWith(".instructure.com")) return undefined;
  const parts = host.split(".");
  if (parts.length < 3) return undefined;
  return parts[0];
}

function postToIframe(
  iframeWin: Window | null | undefined,
  extensionTargetOrigin: string,
  payload: { type: string; payload?: unknown },
) {
  if (!iframeWin) return;
  iframeWin.postMessage(payload, extensionTargetOrigin);
}

function setInputValueReactFriendly(el: HTMLInputElement, value: string) {
  const proto = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
  if (proto?.set) {
    proto.set.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

async function waitFor<T>(
  fn: () => T | null | undefined,
  timeoutMs: number,
  pollMs = 100,
): Promise<T | null> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const v = fn();
    if (v != null) return v;
    await sleep(pollMs);
  }
  return null;
}

function observeUntil<T>(
  doc: Document,
  fn: () => T | null,
  timeoutMs: number,
): Promise<T | null> {
  return new Promise((resolve) => {
    let done = false;
    const finish = (v: T | null) => {
      if (done) return;
      done = true;
      obs.disconnect();
      clearTimeout(tid);
      resolve(v);
    };
    const tryOnce = () => {
      const v = fn();
      if (v != null) finish(v);
    };
    tryOnce();
    const obs = new MutationObserver(() => tryOnce());
    obs.observe(doc.documentElement, { childList: true, subtree: true, attributes: true });
    const tid = window.setTimeout(() => finish(null), timeoutMs);
  });
}

const SETTINGS_PATH = "/profile/settings";
const SCRAPER_DEADLINE_MS = 120_000;
const HANDSHAKE_WAIT_MS = 25_000;
const GATE_WAIT_MS = 20_000;

function isProfileSettingsPathname(pathname: string): boolean {
  return pathname === SETTINGS_PATH || pathname.endsWith("/profile/settings");
}

async function runTokenScraper(): Promise<ExemiCanvasTokenResultPayload> {
  const deadline = Date.now() + SCRAPER_DEADLINE_MS;
  const timeLeft = () => Math.max(0, deadline - Date.now());

  const newTokenLink = await observeUntil(
    document,
    () => document.querySelector<HTMLAnchorElement>("a.add_access_token_link"),
    Math.min(GATE_WAIT_MS, timeLeft()),
  );

  if (!newTokenLink) {
    return { ok: false, code: "NO_NEW_TOKEN_BUTTON" };
  }

  newTokenLink.click();
  await sleep(300);

  const purpose = await waitFor(
    () => document.querySelector<HTMLInputElement>('input[name="purpose"]'),
    Math.min(15_000, timeLeft()),
  );
  if (!purpose) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  setInputValueReactFriendly(purpose, "exemi");

  const dateEl = await waitFor(
    () => document.querySelector<HTMLInputElement>('[data-testid="expiration-date"]'),
    Math.min(15_000, timeLeft()),
  );
  if (!dateEl) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  setInputValueReactFriendly(dateEl, expiryDateYyyyMmDd());

  const timeEl = await waitFor(
    () => document.querySelector<HTMLInputElement>('[data-testid="expiration-time"]'),
    Math.min(10_000, timeLeft()),
  );
  if (!timeEl) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  setInputValueReactFriendly(timeEl, "00:00");

  const genBtn =
    document.querySelector<HTMLButtonElement>('button[aria-label="Generate token"]') ||
    (await waitFor(
      () => {
        const buttons = document.querySelectorAll<HTMLButtonElement>("button[type='submit']");
        for (const b of buttons) {
          if (b.textContent?.includes("Generate token")) return b;
        }
        return null;
      },
      Math.min(5000, timeLeft()),
    ));

  if (!genBtn) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  genBtn.click();

  const tokenSpan = await observeUntil(
    document,
    () => document.querySelector<HTMLElement>('[data-testid="visible_token"]'),
    Math.min(30_000, timeLeft()),
  );

  if (!tokenSpan) {
    return { ok: false, code: "TOKEN_NOT_FOUND" };
  }

  const token = (tokenSpan.textContent || "").trim();
  if (!/^\d+~[\w-]+$/.test(token) || token.length < 20) {
    return { ok: false, code: "TOKEN_NOT_FOUND" };
  }

  const closeClicked =
    (() => {
      const buttons = document.querySelectorAll("button");
      for (const b of buttons) {
        const sr = b.querySelector('[class*="screenReaderContent"]');
        if (sr?.textContent?.trim() === "Close") {
          (b as HTMLButtonElement).click();
          return true;
        }
      }
      const iconClose = document.querySelector('button svg[name="IconX"]');
      if (iconClose) {
        const btn = iconClose.closest("button");
        if (btn) {
          btn.click();
          return true;
        }
      }
      return false;
    })();

  if (!closeClicked) {
    return { ok: false, code: "CLOSE_MODAL_FAILED" };
  }

  const sub = canvasUniversitySubdomain(window.location.hostname);
  return { ok: true, token, universitySubdomain: sub };
}

export type CanvasTokenAutomationOptions = {
  getIframeWindow: () => Window | null | undefined;
};

/**
 * Installs window message listener and drives redirect + scraper. Call once (e.g. from SidebarApp useEffect).
 */
export function installCanvasTokenAutomation(options: CanvasTokenAutomationOptions): () => void {
  let scrapingInFlight = false;
  let lastReady: ExemiAutomationReadyPayload | null = null;
  let handshakeResolver: (() => void) | null = null;

  const extOrigin = extensionOrigin();

  const notifyIframe = (payload: ExemiCanvasTokenResultPayload) => {
    postToIframe(options.getIframeWindow(), extOrigin, {
      type: EXEMI_CANVAS_TOKEN_RESULT,
      payload,
    });
  };

  const sendRedirecting = () => {
    postToIframe(options.getIframeWindow(), extOrigin, {
      type: EXEMI_AUTOMATION_REDIRECTING,
    });
  };

  const onMessage = (event: MessageEvent) => {
    if (!isExtensionIframeOrigin(event.origin)) return;
    if (event.origin !== extOrigin) return;

    const data = event.data;
    if (!data || typeof data !== "object") return;
    if ((data as { type?: string }).type !== EXEMI_AUTOMATION_READY) return;

    const payload = (data as { payload?: ExemiAutomationReadyPayload }).payload;
    if (!payload || typeof payload.isOnboarding !== "boolean") return;

    lastReady = payload;
    handshakeResolver?.();
    handshakeResolver = null;

    if (!payload.isOnboarding) return;

    const path = window.location.pathname;
    const onSettings = isProfileSettingsPathname(path);
    const state = readAutomationState();
    const phase = state?.phase ?? "idle";

    if (!onSettings) {
      if (phase === "redirecting" || phase === "scraping") {
        clearAutomationState();
        scrapingInFlight = false;
        return;
      }
      if (scrapingInFlight) return;
      writeAutomationState("redirecting");
      sendRedirecting();
      window.setTimeout(() => {
        window.location.assign(`${window.location.origin}${SETTINGS_PATH}`);
      }, 50);
      return;
    }

    if (phase === "redirecting") {
      void runScrapeFlow();
    }
  };

  async function runScrapeFlow() {
    if (scrapingInFlight) return;
    scrapingInFlight = true;
    writeAutomationState("scraping");

    const waitHandshake = new Promise<void>((resolve) => {
      if (lastReady?.isOnboarding) {
        resolve();
        return;
      }
      handshakeResolver = resolve;
      window.setTimeout(() => {
        if (handshakeResolver === resolve) {
          handshakeResolver = null;
          resolve();
        }
      }, HANDSHAKE_WAIT_MS);
    });

    await waitHandshake;

    if (!lastReady?.isOnboarding) {
      scrapingInFlight = false;
      clearAutomationState();
      notifyIframe({ ok: false, code: "IFRAME_HANDSHAKE_TIMEOUT" });
      return;
    }

    try {
      const result = await runTokenScraper();
      if (result.ok) {
        writeAutomationState("done");
      } else {
        writeAutomationState("failed");
      }
      notifyIframe(result);
    } catch {
      writeAutomationState("failed");
      notifyIframe({ ok: false, code: "UNKNOWN" });
    } finally {
      scrapingInFlight = false;
      window.setTimeout(() => clearAutomationState(), 5000);
    }
  }

  window.addEventListener("message", onMessage);
  return () => window.removeEventListener("message", onMessage);
}
