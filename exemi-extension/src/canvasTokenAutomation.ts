import {
  CANVAS_TOKEN_AUTOMATION_SS_KEY,
  CANVAS_TOKEN_RETURN_URL_SS_KEY,
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
import { setAutomationOverlayVisible } from "./automationOverlay";

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

function normalizePathnameTrailingSlash(pathname: string): string {
  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }
  return pathname;
}

function isProfileSettingsPathname(pathname: string): boolean {
  const p = normalizePathnameTrailingSlash(pathname);
  return p === SETTINGS_PATH || p.endsWith("/profile/settings");
}

function clearStoredReturnUrlAfterToken(): void {
  try {
    sessionStorage.removeItem(CANVAS_TOKEN_RETURN_URL_SS_KEY);
  } catch {
    // ignore
  }
}

/** Remember where the user was before we send them to profile/settings (same Canvas origin). */
function saveReturnUrlBeforeSettingsRedirect(): void {
  try {
    if (isProfileSettingsPathname(window.location.pathname)) return;
    const p = window.location.pathname + window.location.search + window.location.hash;
    sessionStorage.setItem(CANVAS_TOKEN_RETURN_URL_SS_KEY, p);
  } catch {
    // ignore
  }
}

function pathnameOnlyFromReturnStored(raw: string): string {
  const noHash = raw.split("#")[0] ?? "";
  return noHash.split("?")[0] ?? "";
}

/** Hide overlay and return to the pre-settings Canvas URL if we saved one (success or failure). */
function finishAutomationNavigationToReturnUrl(delayMs: number): void {
  setAutomationOverlayVisible(false);
  try {
    const raw = sessionStorage.getItem(CANVAS_TOKEN_RETURN_URL_SS_KEY);
    clearStoredReturnUrlAfterToken();
    if (!raw) return;
    if (!raw.startsWith("/") || raw.startsWith("//")) return;
    if (isProfileSettingsPathname(pathnameOnlyFromReturnStored(raw))) return;
    window.setTimeout(() => {
      window.location.assign(`${window.location.origin}${raw}`);
    }, delayMs);
  } catch {
    // ignore
  }
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

function collectDocumentAndShadowRoots(): (Document | ShadowRoot)[] {
  const roots: (Document | ShadowRoot)[] = [document];
  for (const el of document.querySelectorAll("*")) {
    if (el.shadowRoot) roots.push(el.shadowRoot);
  }
  return roots;
}

function dispatchKey(target: EventTarget, key: string, code: string) {
  target.dispatchEvent(
    new KeyboardEvent("keydown", { key, code, bubbles: true, cancelable: true }),
  );
  target.dispatchEvent(
    new KeyboardEvent("keyup", { key, code, bubbles: true, cancelable: true }),
  );
}

function safeCssId(id: string): string {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(id);
  }
  return id.replace(/[^a-zA-Z0-9_-]/g, "\\$&");
}

function setNativeInputValue(el: HTMLInputElement, value: string) {
  const proto = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
  if (proto?.set) proto.set.call(el, value);
  else el.value = value;
}

function parseIsoYmd(iso: string): { y: number; m: number; d: number } | null {
  const p = iso.split("-").map(Number);
  if (p.length !== 3 || p.some((n) => !Number.isFinite(n))) return null;
  return { y: p[0], m: p[1], d: p[2] };
}

/** Canvas commits dates as e.g. "1 January 2020" after Enter/blur. */
function expirationDisplayMatchesIso(displayValue: string, iso: string): boolean {
  const v = displayValue.trim();
  if (!v) return false;
  const expect = parseIsoYmd(iso);
  if (!expect) return false;
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    return v === iso;
  }
  const t = Date.parse(v);
  if (Number.isNaN(t)) return false;
  const dt = new Date(t);
  return dt.getFullYear() === expect.y && dt.getMonth() + 1 === expect.m && dt.getDate() === expect.d;
}

function getExpirationDateInput(): HTMLInputElement | null {
  return querySelectorDeep(document, '[data-testid="expiration-date"]') as HTMLInputElement | null;
}

async function commitExpirationDateField(input: HTMLInputElement) {
  input.focus();
  await sleep(40);
  const enterInit: KeyboardEventInit = {
    key: "Enter",
    code: "Enter",
    keyCode: 13,
    which: 13,
    bubbles: true,
    cancelable: true,
  };
  input.dispatchEvent(new KeyboardEvent("keydown", enterInit));
  input.dispatchEvent(new KeyboardEvent("keypress", enterInit));
  input.dispatchEvent(new KeyboardEvent("keyup", enterInit));
  await sleep(80);
  const purpose = querySelectorDeep(document, 'input[name="purpose"]') as HTMLInputElement | null;
  if (purpose) {
    purpose.focus();
    try {
      purpose.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, cancelable: true }));
    } catch {
      purpose.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }));
    }
  }
  input.blur();
  await sleep(120);
}

async function waitForExpirationDateCommitted(iso: string, timeoutMs: number): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const inp = getExpirationDateInput();
    if (inp && expirationDisplayMatchesIso(inp.value, iso)) {
      if (inp.getAttribute("aria-invalid") !== "true") return true;
    }
    await sleep(100);
  }
  const last = getExpirationDateInput();
  return Boolean(
    last && expirationDisplayMatchesIso(last.value, iso) && last.getAttribute("aria-invalid") !== "true",
  );
}

function parseMonthYearFromCalendarHeader(text: string): { y: number; m: number } | null {
  const m = text.match(
    /(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})/i,
  );
  if (!m) return null;
  const d = new Date(`${m[1]} 1, ${m[2]}`);
  if (Number.isNaN(d.getTime())) return null;
  return { y: d.getFullYear(), m: d.getMonth() + 1 };
}

function findVisibleCalendarGrid(): { grid: Element; header: Element | null } | null {
  for (const root of collectDocumentAndShadowRoots()) {
    for (const grid of root.querySelectorAll('[role="grid"]')) {
      const el = grid as HTMLElement;
      if (el.offsetParent === null && el.getClientRects().length === 0) continue;
      const host = grid.closest('[role="dialog"], [data-position-target]') || grid.parentElement;
      const header =
        host?.querySelector("h2, h3, [class*='header']") ||
        grid.previousElementSibling ||
        null;
      return { grid, header };
    }
  }
  return null;
}

function findExpirationPopoverRoot(input: HTMLInputElement): Element | null {
  const targetId = input.getAttribute("data-position-target");
  if (targetId) {
    for (const root of collectDocumentAndShadowRoots()) {
      const hit = root.querySelector(`#${safeCssId(targetId)}`);
      if (hit) return hit;
    }
  }
  const ac = input.getAttribute("aria-controls");
  if (ac) {
    for (const root of collectDocumentAndShadowRoots()) {
      const node = root.querySelector(`#${safeCssId(ac)}`);
      if (node) {
        return (
          node.closest('[role="presentation"]') ||
          node.closest('[role="dialog"]') ||
          node.parentElement
        );
      }
    }
  }
  return null;
}

function findCalendarGridForExpirationInput(
  input: HTMLInputElement,
): { grid: Element; header: Element | null } | null {
  const pop = findExpirationPopoverRoot(input);
  if (pop) {
    const grid = pop.querySelector('[role="grid"]');
    if (grid) {
      const gh = grid as HTMLElement;
      if (gh.offsetParent !== null || gh.getClientRects().length > 0) {
        return {
          grid,
          header:
            pop.querySelector("h2, h3, [class*='month'], [class*='header']") ||
            pop.querySelector("span") ||
            null,
        };
      }
    }
  }
  return findVisibleCalendarGrid();
}

function findCalendarMonthNav(grid: Element): { prev?: HTMLElement; next?: HTMLElement } {
  const scope = grid.closest('[role="dialog"]') || grid.parentElement || document.body;
  let prev: HTMLElement | undefined;
  let next: HTMLElement | undefined;
  for (const b of scope.querySelectorAll("button")) {
    const label = (b.getAttribute("aria-label") || "").toLowerCase();
    const svg = b.querySelector("svg");
    const name = svg?.getAttribute("name") || "";
    if (label.includes("previous") || label.includes("prev") || /arrow.*start|left/i.test(name)) {
      prev = b as HTMLElement;
    }
    if (label.includes("next") || /arrow.*end|right/i.test(name)) {
      next = b as HTMLElement;
    }
  }
  return { prev, next };
}

async function typeDateLikeUser(input: HTMLInputElement, iso: string) {
  input.focus();
  await sleep(40);
  setNativeInputValue(input, "");
  input.dispatchEvent(
    new InputEvent("input", { bubbles: true, cancelable: true, inputType: "deleteContentBackward" }),
  );
  for (const char of iso) {
    const next = input.value + char;
    setNativeInputValue(input, next);
    input.dispatchEvent(
      new InputEvent("input", {
        bubbles: true,
        cancelable: true,
        inputType: "insertText",
        data: char,
      }),
    );
    await sleep(22);
  }
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

async function tryPlainTextExpirationDate(input: HTMLInputElement, iso: string): Promise<boolean> {
  input.focus();
  await sleep(60);
  dispatchKey(input, "Escape", "Escape");
  dispatchKey(document.body, "Escape", "Escape");
  await sleep(120);
  input.focus();
  await sleep(60);
  setNativeInputValue(input, "");
  input.dispatchEvent(
    new InputEvent("input", { bubbles: true, cancelable: true, inputType: "deleteContentBackward" }),
  );
  setNativeInputValue(input, iso);
  input.dispatchEvent(
    new InputEvent("input", {
      bubbles: true,
      cancelable: true,
      inputType: "insertText",
      data: iso,
    }),
  );
  input.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(100);
  if (input.value.trim() === iso) return true;

  await typeDateLikeUser(input, iso);
  await sleep(120);
  return input.value.trim() === iso;
}

async function pickExpirationDateViaCalendar(input: HTMLInputElement, iso: string): Promise<boolean> {
  const parts = iso.split("-").map(Number);
  const targetYear = parts[0];
  const targetMonth = parts[1];
  const targetDay = parts[2];
  if (!targetYear || !targetMonth || !targetDay) return false;

  input.focus();
  input.click();
  await sleep(450);

  const found = await waitFor(() => findCalendarGridForExpirationInput(input), 10_000, 150);
  if (!found) return false;

  const { grid, header } = found;
  const nav = findCalendarMonthNav(grid);

  for (let step = 0; step < 36; step++) {
    const label =
      (header?.textContent || grid.parentElement?.textContent || "").replace(/\s+/g, " ").trim();
    const cur = parseMonthYearFromCalendarHeader(label);
    if (cur && cur.y === targetYear && cur.m === targetMonth) break;
    if (!cur) break;
    const want = targetYear * 12 + targetMonth;
    const have = cur.y * 12 + cur.m;
    if (want > have) {
      if (!nav.next) break;
      nav.next.click();
    } else {
      if (!nav.prev) break;
      nav.prev.click();
    }
    await sleep(220);
  }

  const dayStr = String(targetDay);
  const candidates = grid.querySelectorAll("button, [role='gridcell'] button, [role='option']");
  for (const cell of candidates) {
    if (!(cell instanceof HTMLElement)) continue;
    if (cell.textContent?.trim() !== dayStr) continue;
    if (cell.getAttribute("aria-disabled") === "true") continue;
    if ((cell as HTMLButtonElement).disabled) continue;
    const op = parseFloat(getComputedStyle(cell).opacity || "1");
    if (op < 0.45) continue;
    cell.click();
    await sleep(200);
    return true;
  }

  return false;
}

async function fillInstUiExpirationDate(input: HTMLInputElement, iso: string): Promise<boolean> {
  const seeded =
    (await tryPlainTextExpirationDate(input, iso)) ||
    (await pickExpirationDateViaCalendar(input, iso));
  if (!seeded) return false;

  await commitExpirationDateField(input);
  if (await waitForExpirationDateCommitted(iso, 14_000)) return true;

  await commitExpirationDateField(input);
  return waitForExpirationDateCommitted(iso, 10_000);
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
  const isoDate = expiryDateYyyyMmDd();
  const dateOk = await fillInstUiExpirationDate(dateEl, isoDate);
  if (!dateOk) {
    return { ok: false, code: "FORM_TIMEOUT" };
  }
  await sleep(150);

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
      // Only "scraping" off settings means the user left profile/settings mid-run.
      // "redirecting" on a non-settings page is normal: we set it here, then assign()
      // after a short delay; duplicate EXEMI_AUTOMATION_READY must not clear the
      // stored return URL or we never navigate back after success.
      if (phase === "scraping") {
        setAutomationOverlayVisible(false);
        clearStoredReturnUrlAfterToken();
        clearAutomationState();
        scrapingInFlight = false;
        return;
      }
      if (scrapingInFlight) return;
      setAutomationOverlayVisible(true);
      saveReturnUrlBeforeSettingsRedirect();
      writeAutomationState("redirecting");
      sendRedirecting();
      window.setTimeout(() => {
        window.location.assign(`${window.location.origin}${SETTINGS_PATH}`);
      }, 50);
      return;
    }

    const resume = Boolean((payload as ExemiAutomationReadyPayload).automationResume);
    const shouldStart = phase === "redirecting" || (phase === "idle" && resume);
    if (shouldStart) {
      setAutomationOverlayVisible(true);
      if (phase === "idle" && resume) {
        writeAutomationState("redirecting");
      }
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
      notifyIframe({ ok: false, code: "IFRAME_HANDSHAKE_TIMEOUT" });
      finishAutomationNavigationToReturnUrl(450);
      clearAutomationState();
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
      if (result.ok) {
        finishAutomationNavigationToReturnUrl(350);
      } else {
        finishAutomationNavigationToReturnUrl(550);
      }
    } catch {
      writeAutomationState("failed");
      notifyIframe({ ok: false, code: "UNKNOWN" });
      finishAutomationNavigationToReturnUrl(550);
    } finally {
      scrapingInFlight = false;
      window.setTimeout(() => clearAutomationState(), 5000);
    }
  }

  window.addEventListener("message", onMessage);
  return () => window.removeEventListener("message", onMessage);
}
