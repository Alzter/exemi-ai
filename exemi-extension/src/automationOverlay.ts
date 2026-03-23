/**
 * Full-page automation overlay visibility (Canvas tab). Survives reloads via sessionStorage;
 * same-tab updates use a window event for React.
 */
export const EXEMI_AUTOMATION_OVERLAY_SS_KEY = "exemi_cs_automation_overlay";

/**
 * Set on Canvas origin before success `location.assign` back to the pre-settings URL.
 * On the next load, `consumeAutomationOverlayAfterSuccessReturn()` clears the loading overlay.
 */
const EXEMI_OVERLAY_DISMISS_AFTER_SUCCESS_RETURN_KEY =
  "exemi_cs_overlay_dismiss_after_success_return";

export function armOverlayDismissAfterSuccessfulCanvasReturn(): void {
  try {
    sessionStorage.setItem(EXEMI_OVERLAY_DISMISS_AFTER_SUCCESS_RETURN_KEY, "1");
  } catch {
    // ignore
  }
}

/**
 * Content shell: if we just landed after a successful token flow navigation, hide overlay
 * without flashing it on first paint.
 */
export function consumeAutomationOverlayAfterSuccessReturn(): boolean {
  try {
    if (sessionStorage.getItem(EXEMI_OVERLAY_DISMISS_AFTER_SUCCESS_RETURN_KEY) !== "1") {
      return false;
    }
    sessionStorage.removeItem(EXEMI_OVERLAY_DISMISS_AFTER_SUCCESS_RETURN_KEY);
    sessionStorage.removeItem(EXEMI_AUTOMATION_OVERLAY_SS_KEY);
    return true;
  } catch {
    return false;
  }
}

export function setAutomationOverlayVisible(visible: boolean): void {
  try {
    if (visible) {
      sessionStorage.setItem(EXEMI_AUTOMATION_OVERLAY_SS_KEY, "1");
    } else {
      sessionStorage.removeItem(EXEMI_AUTOMATION_OVERLAY_SS_KEY);
    }
  } catch {
    // ignore
  }
  window.dispatchEvent(
    new CustomEvent("exemi-automation-overlay", { detail: { visible } }),
  );
}

export function readAutomationOverlayVisible(): boolean {
  try {
    return sessionStorage.getItem(EXEMI_AUTOMATION_OVERLAY_SS_KEY) === "1";
  } catch {
    return false;
  }
}
