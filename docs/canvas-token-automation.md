# Automatic Canvas API token setup (browser extension)

This document describes **why** Exemi automates creation of a Canvas “manual” access token, **how** the extension and iframe app cooperate, and **implementation details** that matter for maintenance and security.

For build and packaging of the extension, see [exemi-extension/README.md](../exemi-extension/README.md).

---

## Rationale

### Why a token at all

Exemi talks to the **Canvas REST API** on the user’s behalf (courses, assignments, etc.). That requires credentials the backend can use server-side. Many institutions do not expose OAuth for third-party apps in a way Exemi can register for, while Canvas still allows users to create **personal access tokens** under **Account → Settings → Approved integrations**.

### Why automate it

Manual copy-paste is error-prone and adds friction during onboarding—especially for users who already have the extension open inside Canvas. Automating the **“New access token”** flow in the logged-in Canvas tab:

- Reduces steps and support burden.
- Keeps the secret handling in the user’s browser: the content script reads the token from the Canvas UI and passes it only to the trusted extension iframe, which can then submit it to Exemi’s API like any other form.

### Design goals

1. **Work without Canvas OAuth** where institutions only offer manual tokens.
2. **Survive full page navigations** (Canvas redirects to `/profile/settings` and reloads the tab).
3. **Avoid surprising the user**: a full-viewport loading overlay explains that Exemi is configuring itself while automation runs.
4. **On success**, return the user to the Canvas page they were on before settings (when that URL was saved).
5. **On failure**, return to that same page when possible, hide the overlay, and surface a clear error in the **extension sidebar** (iframe app).

---

## Architecture overview

```mermaid
sequenceDiagram
  participant IF as Extension iframe (exemi-frontend)
  participant CS as Content script (Canvas page)
  participant C as Canvas DOM

  IF->>CS: postMessage EXEMI_AUTOMATION_READY (onboarding, resume flags)
  alt Not on profile/settings
    CS->>IF: EXEMI_AUTOMATION_REDIRECTING
    CS->>C: location.assign(/profile/settings)
  end
  Note over CS,C: Full navigation; CS reinjects
  IF->>CS: EXEMI_AUTOMATION_READY (again)
  CS->>C: DOM automation (open dialog, fill, submit, read token)
  CS->>IF: EXEMI_CANVAS_TOKEN_RESULT (ok + token or error code)
  CS->>C: Optional return navigation to saved URL
```

- **Iframe** runs on the **extension origin** (`moz-extension:` / `chrome-extension:`). It performs onboarding UI and API calls; it cannot directly script Canvas.
- **Content script** runs in the **Canvas page** and can access the Canvas DOM. It listens for messages from the iframe and drives navigation plus scraping.
- **postMessage** is the bridge. Message **types and payloads** are defined in two copies of the same module (must stay aligned):

  - `exemi-extension/src/extensionAutomationMessages.ts`
  - `exemi-frontend/src/extensionAutomationMessages.ts`

---

## Trust and messaging

### Iframe → content script (`EXEMI_AUTOMATION_READY`)

The content script only accepts automation handshakes from the **Exemi iframe**, not random pages:

- Prefer `event.source === iframe.contentWindow` (works well in Firefox).
- Fall back to extension-origin checks via `isTrustedIframeAutomationMessage` in `postMessageToExemiIframe.ts`.

### Content script → iframe (`EXEMI_AUTOMATION_REDIRECTING`, `EXEMI_CANVAS_TOKEN_RESULT`)

Chromium and Firefox differ on the iframe’s effective `postMessage` target origin for extension iframes embedded in a web page. The portable approach is **`postMessage(..., "*")` to the iframe `contentWindow` reference only**—delivery is still scoped to that window, not a broadcast to the page.

---

## Session and resume state

### Canvas `sessionStorage` (automation phase)

Key: `exemi_cs_token_automation` (`CANVAS_TOKEN_AUTOMATION_SS_KEY`).

Phases: `idle` | `redirecting` | `scraping` | `done` | `failed`.

This survives **in-tab** navigations on the same Canvas origin so that after redirect to settings the content script knows scraping should start instead of redirecting again.

**Important behaviour:** A second `EXEMI_AUTOMATION_READY` while still on the pre-settings page with phase `redirecting` must **not** be treated as “user left settings.” Only phase `scraping` on a non-settings URL means the user navigated away mid-run; clearing the stored “return URL” on duplicate `redirecting` was a bug that prevented returning after success.

### Extension iframe `sessionStorage`

| Key | Purpose |
|-----|--------|
| `exemi_iframe_token_automation_resume` | Set when redirect is announced; tells the next READY that automation should resume after reload. |
| `exemi_iframe_automation_session_pending` | Set while onboarding is mounted; helps resume if the redirect message is missed. |
| `exemi_canvas_token_failure` | On failure, stores `{ code }` so after Canvas navigates back the app can show [ExtensionIncompatible](../exemi-frontend/src/pages/ExtensionIncompatible.tsx). |

### Canvas return URL

Key: `exemi_cs_return_after_token` (`CANVAS_TOKEN_RETURN_URL_SS_KEY`).

Before sending the user to `/profile/settings`, the content script saves `pathname + search + hash`. After success **or** failure (when configured), navigation restores that URL when it is safe (same origin, not settings path).

---

## User-visible overlay

Key: `exemi_cs_automation_overlay` plus a window event `exemi-automation-overlay`.

- Persisted in Canvas `sessionStorage` so the overlay stays “on” across full reloads.
- Dispatched as a `CustomEvent` so the React shell can update immediately without reload.
- Implemented in `exemi-extension/src/automationOverlay.ts`, rendered by `LoadingOverlay` in `exemi-extension/src/loading.tsx`, styled in `sidebar.css`. The overlay stacks **above** the sidebar so the user cannot interact with Canvas or the iframe until automation finishes.
- **Success + return navigation:** the overlay stays up while the iframe receives the token and until Canvas has navigated back to the saved URL. Session key `exemi_cs_overlay_dismiss_after_success_return` arms that transition; on the next load, `consumeAutomationOverlayAfterSuccessReturn()` in the content shell clears the overlay before first paint so the user does not briefly see the prefilled magic form under a loading card.
- **Failure** (or success with nowhere to return): the overlay is cleared immediately before any `location.assign`, so the sidebar error UI is visible during the trip back.

---

## DOM automation (content script)

Implemented in `exemi-extension/src/canvasTokenAutomation.ts`.

- Targets **Profile → Settings** (`/profile/settings`, with pathname normalization for trailing slashes).
- Canvas **InstUI** often renders inside **shadow DOM**; the scraper uses deep queries and polling, not only `document.querySelector`.
- Finds controls by accessible text heuristics (e.g. “new access token”), fills purpose/expiry, submits, reads the generated token from the page, and closes the modal when possible.
- Token expiry offset is configurable via **`VITE_CANVAS_TOKEN_EXPIRY_DAYS`** (extension build).

Failure codes (`ExemiTokenFailureCode`) distinguish timeouts, missing UI, token not found, etc., for support and UI copy.

---

## Frontend integration

- **`useExtensionCanvasTokenAutomation`** (`exemi-frontend/src/useExtensionCanvasTokenAutomation.ts`): sends `EXEMI_AUTOMATION_READY` with `isOnboarding` and `automationResume`, handles `EXEMI_AUTOMATION_REDIRECTING` and `EXEMI_CANVAS_TOKEN_RESULT`, maintains resume/failure sticky keys.
- **Onboarding** (`exemi-frontend/src/pages/onboarding/index.tsx`): mounts automation hook; on success pre-fills the magic token form; on failure navigates to the incompatible route and relies on sticky state after Canvas navigates away.
- **`LoggedInFlow`** (`exemi-frontend/src/pages/app/index.tsx`): if the iframe loads with a pending failure sticky key, navigates to `extension_incompatible/` so the error is not lost after a full navigation.

---

## Key source files

| Area | Path |
|------|------|
| Content shell + overlay mount | `exemi-extension/src/content.tsx` |
| Overlay state API | `exemi-extension/src/automationOverlay.ts` |
| Loading UI | `exemi-extension/src/Loading.tsx` |
| Scraper + state machine | `exemi-extension/src/canvasTokenAutomation.ts` |
| postMessage helpers + trust | `exemi-extension/src/postMessageToExemiIframe.ts` |
| Shared message constants (×2) | `exemi-extension/…/extensionAutomationMessages.ts`, `exemi-frontend/…/extensionAutomationMessages.ts` |
| Iframe hook | `exemi-frontend/src/useExtensionCanvasTokenAutomation.ts` |
| Error page | `exemi-frontend/src/pages/ExtensionIncompatible.tsx` |

---

## Why not put all of this in README.md?

The root and extension READMEs stay short for onboarding new contributors. This flow is **cross-cutting** (extension + frontend + UX policy) and benefits from a **single narrative** and diagrams; linking here from the extension README keeps discovery easy without inflating the main README.
