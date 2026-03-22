/**
 * Full-page automation overlay visibility (Canvas tab). Survives reloads via sessionStorage;
 * same-tab updates use a window event for React.
 */
export const EXEMI_AUTOMATION_OVERLAY_SS_KEY = "exemi_cs_automation_overlay";

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
