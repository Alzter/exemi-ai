import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import sidebarCss from "./sidebar.css?inline";

const ROOT_ID = "exemi-root";
const OPEN_KEY = "exemi_sidebar_open";

/** Must match exemi-frontend `EXEMI_CANVAS_CONTEXT_MESSAGE`. */
const EXEMI_CANVAS_CONTEXT_MESSAGE = "EXEMI_CANVAS_CONTEXT";

type CanvasPagePayload = { href: string; path: string; query: string };

function getExtensionRuntime(): { getURL: (path: string) => string } {
  const g = globalThis as typeof globalThis & {
    browser?: { runtime: { getURL: (path: string) => string } };
    chrome?: { runtime: { getURL: (path: string) => string } };
  };
  if (g.browser?.runtime?.getURL) return g.browser.runtime;
  if (g.chrome?.runtime?.getURL) return g.chrome.runtime;
  throw new Error("Extension runtime API not available");
}

function ExemiAppIframe({ pageContext }: { pageContext: CanvasPagePayload }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pageContextRef = useRef(pageContext);
  pageContextRef.current = pageContext;

  const iframeSrc = useMemo(() => {
    try {
      return getExtensionRuntime().getURL("exemi-frontend/index.html");
    } catch {
      return "about:blank";
    }
  }, []);

  const targetOrigin = useMemo(() => {
    try {
      return new URL(getExtensionRuntime().getURL("")).origin;
    } catch {
      return "*";
    }
  }, []);

  const postContext = useCallback(() => {
    const win = iframeRef.current?.contentWindow;
    if (!win) return;
    const origin = targetOrigin === "*" ? "*" : targetOrigin;
    win.postMessage(
      {
        type: EXEMI_CANVAS_CONTEXT_MESSAGE,
        payload: pageContextRef.current,
      },
      origin,
    );
  }, [targetOrigin]);

  useEffect(() => {
    postContext();
  }, [pageContext, postContext]);

  return (
    <iframe
      ref={iframeRef}
      className="exemi-app-iframe"
      src={iframeSrc}
      title="Exemi"
      onLoad={postContext}
    />
  );
}

function isCanvasLoggedIn(): boolean {
  try {
    const session = localStorage.getItem("canvas_session");
    if (typeof session === "string" && session.trim().length > 0) return true;
  } catch {
    // ignore
  }

  try {
    const bodyClass = document.body?.className || "";
    if (bodyClass.includes("context-user_")) return true;
    if (document.getElementById("global_nav_profile_link")) return true;
  } catch {
    // ignore
  }

  return false;
}

function getInitialOpen(): boolean {
  try {
    return localStorage.getItem(OPEN_KEY) !== "0";
  } catch {
    return true;
  }
}

function setOpen(open: boolean) {
  try {
    localStorage.setItem(OPEN_KEY, open ? "1" : "0");
  } catch {
    // ignore
  }
}

function useCanvasUrl(): string {
  const [url, setUrl] = useState(() => window.location.href);

  useEffect(() => {
    let last = window.location.href;
    const update = () => {
      const next = window.location.href;
      if (next !== last) {
        last = next;
        setUrl(next);
      }
    };

    const onPop = () => update();
    window.addEventListener("popstate", onPop);
    window.addEventListener("hashchange", onPop);

    // Patch history for Canvas SPA navigation.
    const origPush = history.pushState;
    const origReplace = history.replaceState;

    history.pushState = function (...args) {
      origPush.apply(this, args);
      update();
    };
    history.replaceState = function (...args) {
      origReplace.apply(this, args);
      update();
    };

    const timer = window.setInterval(update, 1000);

    return () => {
      window.removeEventListener("popstate", onPop);
      window.removeEventListener("hashchange", onPop);
      history.pushState = origPush;
      history.replaceState = origReplace;
      window.clearInterval(timer);
    };
  }, []);

  return url;
}

function SidebarApp() {
  const [open, setOpenState] = useState(getInitialOpen);
  const url = useCanvasUrl();

  const pageContext = useMemo(() => {
    try {
      const u = new URL(url);
      return {
        href: u.href,
        path: u.pathname,
        query: u.search,
      };
    } catch {
      return { href: url, path: "", query: "" };
    }
  }, [url]);

  useEffect(() => {
    setOpen(open);
  }, [open]);

  return (
    <div className="wrap">
      <div className="exemi-iframe-host">
        <ExemiAppIframe pageContext={pageContext} />
      </div>
    </div>
  );
}

type Injected = {
  rootEl: HTMLDivElement;
  shadow: ShadowRoot;
  reactRoot: Root;
};

function inject(): Injected {
  const existing = document.getElementById(ROOT_ID);
  if (existing) {
    // Shouldn't happen (we remove on logout), but avoid duplicates.
    existing.remove();
  }

  const rootEl = document.createElement("div");
  rootEl.id = ROOT_ID;
  rootEl.style.all = "initial";
  rootEl.style.position = "fixed";
  rootEl.style.top = "0";
  rootEl.style.right = "0";
  rootEl.style.height = "100vh";
  rootEl.style.zIndex = "2147483647";
  rootEl.style.pointerEvents = "none";

  const shadow = rootEl.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = `:host { all: initial; }\n${sidebarCss}`;

  const mount = document.createElement("div");
  mount.style.pointerEvents = "auto";
  shadow.appendChild(style);
  shadow.appendChild(mount);

  document.body.appendChild(rootEl);

  const reactRoot = createRoot(mount);
  reactRoot.render(<SidebarApp />);

  return { rootEl, shadow, reactRoot };
}

let injected: Injected | null = null;

function ensure() {
  if (!document.body) return;

  if (!isCanvasLoggedIn()) {
    if (injected) {
      injected.reactRoot.unmount();
      injected.rootEl.remove();
      injected = null;
    } else {
      const existing = document.getElementById(ROOT_ID);
      if (existing) existing.remove();
    }
    return;
  }

  if (injected) return;
  if (document.getElementById(ROOT_ID)) return;

  injected = inject();
}

// Keep alive across Canvas SPA navigation and async auth changes.
const obs = new MutationObserver(() => ensure());
obs.observe(document.documentElement, { childList: true, subtree: true });

ensure();
setInterval(ensure, 1500);
