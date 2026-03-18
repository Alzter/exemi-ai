(() => {
  const ROOT_ID = "exemi-root";
  const OPEN_KEY = "exemi_sidebar_open";
  const ASSETS = {
    cssPath: "sidebar.css",
    htmlPath: "sidebar.html",
  };

  if (window.__exemiInjected) return;
  window.__exemiInjected = true;

  const assetCache = {
    css: null,
    html: null,
    loading: null,
  };

  async function loadAssetText(relPath) {
    // `chrome.runtime.getURL` exists in Chromium + Firefox extension contexts.
    // Fallback keeps this resilient in other runtimes.
    const url =
      typeof chrome !== "undefined" && chrome?.runtime?.getURL
        ? chrome.runtime.getURL(relPath)
        : relPath;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load ${relPath}: ${res.status}`);
    return await res.text();
  }

  async function ensureAssetsLoaded() {
    if (assetCache.css && assetCache.html) return;
    if (assetCache.loading) return assetCache.loading;

    assetCache.loading = (async () => {
      const [css, html] = await Promise.all([
        loadAssetText(ASSETS.cssPath),
        loadAssetText(ASSETS.htmlPath),
      ]);
      assetCache.css = css;
      assetCache.html = html;
    })();

    return assetCache.loading;
  }

  function isOpen() {
    try {
      return localStorage.getItem(OPEN_KEY) !== "0";
    } catch {
      return true;
    }
  }

  function setOpen(open) {
    try {
      localStorage.setItem(OPEN_KEY, open ? "1" : "0");
    } catch {
      // ignore
    }
  }

  async function ensureInjected() {
    if (!document.body) return false;
    if (document.getElementById(ROOT_ID)) return true;

    await ensureAssetsLoaded();

    const root = document.createElement("div");
    root.id = ROOT_ID;
    root.style.all = "initial";
    root.style.position = "fixed";
    root.style.top = "0";
    root.style.right = "0";
    root.style.height = "100vh";
    root.style.zIndex = "2147483647";
    root.style.pointerEvents = "none";

    const shadow = root.attachShadow({ mode: "open" });

    const style = document.createElement("style");
    style.textContent = `:host { all: initial; }\n${assetCache.css || ""}`;

    const wrap = document.createElement("div");
    wrap.innerHTML = assetCache.html || "";

    const tab = wrap.querySelector(".tab");
    const panel = wrap.querySelector(".panel");
    const closeBtn = wrap.querySelector(".iconBtn");
    const body = wrap.querySelector(".body");
    const composer = wrap.querySelector("form.composer");
    const input = wrap.querySelector("input.input");

    if (!tab || !panel || !closeBtn || !body || !composer || !input) {
      throw new Error("Exemi sidebar template missing required elements");
    }

    function applyOpenState(open) {
      panel.classList.toggle("hidden", !open);
      setOpen(open);
    }

    tab.addEventListener("click", () => applyOpenState(panel.classList.contains("hidden")));
    closeBtn.addEventListener("click", () => applyOpenState(false));

    composer.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = (input.value || "").trim();
      if (!text) return;
      const userBubble = document.createElement("div");
      userBubble.className = "bubble";
      userBubble.textContent = text;
      body.appendChild(userBubble);
      body.scrollTop = body.scrollHeight;
      input.value = "";
    });

    shadow.appendChild(style);
    shadow.appendChild(wrap);
    document.body.appendChild(root);

    applyOpenState(isOpen());
    return true;
  }

  // Canvas is a SPA; body might be swapped/rehydrated.
  // This keeps the sidebar alive without duplicating it.
  const observer = new MutationObserver(() => {
    void ensureInjected();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  void ensureInjected().then((ok) => {
    if (ok) return;
    const timer = setInterval(() => {
      void ensureInjected().then((nowOk) => {
        if (nowOk) clearInterval(timer);
      });
    }, 250);
  });
})();
