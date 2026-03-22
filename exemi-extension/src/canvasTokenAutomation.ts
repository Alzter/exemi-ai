import {
  CANVAS_TOKEN_AUTOMATION_SS_KEY,
  EXEMI_AUTOMATION_READY,
  EXEMI_AUTOMATION_REDIRECTING,
  EXEMI_CANVAS_TOKEN_RESULT,
  type CanvasTokenAutomationState,
  type ExemiAutomationReadyPayload,
  type ExemiCanvasTokenResultPayload,
} from "./extensionAutomationMessages";
import {
  getExtensionOrigin,
  isTrustedIframeAutomationMessage,
  postMessageToExemiIframe,
} from "./postMessageToExemiIframe";

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

const SETTINGS_PATH = "/profile/settings";
const SCRAPER_DEADLINE_MS = 120_000;
const HANDSHAKE_WAIT_MS = 25_000;
/** Canvas often hydrates this section late; keep generous. */
const GATE_WAIT_MS = 60_000;

function isProfileSettingsPathname(pathname: string): boolean {
  return pathname === SETTINGS_PATH || pathname.endsWith("/profile/settings");
}

const NEW_TOKEN_TEXT_NEEDLES = [
  "new access token",
  "add new access token",
  "create access token",
  "+ new access token",
] as const;

function normalizeUiText(s: string): string {
  return s.toLowerCase().replace(/\s+/g, " ").trim();
}

function elementMatchesNewTokenTrigger(el: Element): el is HTMLElement {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName.toLowerCase();
  if (tag !== "a" && tag !== "button" && el.getAttribute("role") !== "button") return false;
  const t = normalizeUiText(el.textContent || "");
  if (!t) return false;
  return NEW_TOKEN_TEXT_NEEDLES.some((n) => t.includes(n));
}

/**
 * Walk document and open shadow roots (Canvas / InstUI often mount inside shadow DOM).
 */
function querySelectorDeep(
  root: Document | ShadowRoot,
  selector: string,
): HTMLElement | null {
  const hit = root.querySelector<HTMLElement>(selector);
  if (hit) return hit;
  for (const el of root.querySelectorAll("*")) {
    if (el.shadowRoot) {
      const inner = querySelectorDeep(el.shadowRoot, selector);
      if (inner) return inner;
    }
  }
  return null;
}

function findNewAccessTokenTrigger(): HTMLElement | null {
  const byClass = querySelectorDeep(document, "a.add_access_token_link");
  if (byClass) return byClass;

  const roots: (Document | ShadowRoot)[] = [document];
  for (const el of document.querySelectorAll("*")) {
    if (el.shadowRoot) roots.push(el.shadowRoot);
  }
  for (const root of roots) {
    for (const el of root.querySelectorAll("a, button, [role='button']")) {
      if (elementMatchesNewTokenTrigger(el)) return el;
    }
  }
  return null;
}

async function runTokenScraper(): Promise<ExemiCanvasTokenResultPayload> {
  const deadline = Date.now() + SCRAPER_DEADLINE_MS;
  const timeLeft = () => Math.max(0, deadline - Date.now());

  await sleep(800);

  const newTokenLink = await waitFor(
    () => findNewAccessTokenTrigger(),
    Math.min(GATE_WAIT_MS, timeLeft()),
    200,
  );

  if (!newTokenLink) {
    return { ok: false, code: "NO_NEW_TOKEN_BUTTON" };
  }

  try {
    newTokenLink.scrollIntoView({ block: "center", inline: "nearest" });
  } catch {
    // ignore
  }
  await sleep(200);
  newTokenLink.click();
  await sleep(300);

  const purpose = await waitFor(
    () => querySelectorDeep(document, 'input[name="purpose"]') as HTMLInputElement | null,
    Math.min(20_000, timeLeft()),
  );
  if (!purpose) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  setInputValueReactFriendly(purpose, "exemi");

  const dateEl = await waitFor(
    () =>
      querySelectorDeep(document, '[data-testid="expiration-date"]') as HTMLInputElement | null,
    Math.min(20_000, timeLeft()),
  );
  if (!dateEl) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  setInputValueReactFriendly(dateEl, expiryDateYyyyMmDd());

  const timeEl = await waitFor(
    () =>
      querySelectorDeep(document, '[data-testid="expiration-time"]') as HTMLInputElement | null,
    Math.min(15_000, timeLeft()),
  );
  if (!timeEl) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  setInputValueReactFriendly(timeEl, "00:00");

  const findGenerateButton = (): HTMLButtonElement | null => {
    const byLabel = querySelectorDeep(document, 'button[aria-label="Generate token"]');
    if (byLabel instanceof HTMLButtonElement) return byLabel;
    const roots: (Document | ShadowRoot)[] = [document];
    for (const el of document.querySelectorAll("*")) {
      if (el.shadowRoot) roots.push(el.shadowRoot);
    }
    for (const root of roots) {
      for (const b of root.querySelectorAll<HTMLButtonElement>("button[type='submit'], button")) {
        if (normalizeUiText(b.textContent || "").includes("generate token")) return b;
      }
    }
    return null;
  };

  const genBtn =
    findGenerateButton() ||
    (await waitFor(findGenerateButton, Math.min(10_000, timeLeft())));

  if (!genBtn) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  genBtn.click();

  const tokenSpan = await waitFor(
    () => querySelectorDeep(document, '[data-testid="visible_token"]'),
    Math.min(45_000, timeLeft()),
    150,
  );

  if (!tokenSpan) {
    return { ok: false, code: "TOKEN_NOT_FOUND" };
  }

  const token = (tokenSpan.textContent || "").trim();
  if (!/^\d+~[\w-]+$/.test(token) || token.length < 20) {
    return { ok: false, code: "TOKEN_NOT_FOUND" };
  }

  const closeClicked = (() => {
    const roots: (Document | ShadowRoot)[] = [document];
    for (const el of document.querySelectorAll("*")) {
      if (el.shadowRoot) roots.push(el.shadowRoot);
    }
    for (const root of roots) {
      for (const b of root.querySelectorAll("button")) {
        const sr = b.querySelector('[class*="screenReaderContent"]');
        if (sr?.textContent?.trim() === "Close") {
          b.click();
          return true;
        }
      }
      const iconClose = root.querySelector('svg[name="IconX"]');
      if (iconClose) {
        const btn = iconClose.closest("button");
        if (btn) {
          btn.click();
          return true;
        }
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

  const extOrigin = getExtensionOrigin();

  const notifyIframe = (payload: ExemiCanvasTokenResultPayload) => {
    postMessageToExemiIframe(options.getIframeWindow(), {
      type: EXEMI_CANVAS_TOKEN_RESULT,
      payload,
    });
  };

  const sendRedirecting = () => {
    postMessageToExemiIframe(options.getIframeWindow(), {
      type: EXEMI_AUTOMATION_REDIRECTING,
    });
  };

  const onMessage = (event: MessageEvent) => {
    if (!isTrustedIframeAutomationMessage(event, options.getIframeWindow(), extOrigin)) {
      return;
    }

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
