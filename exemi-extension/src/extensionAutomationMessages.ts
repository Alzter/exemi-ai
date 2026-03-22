/**
 * Must stay aligned with exemi-frontend/src/extensionAutomationMessages.ts
 * (content bundle cannot import the frontend package).
 */

export const EXEMI_AUTOMATION_READY = "EXEMI_AUTOMATION_READY";
export const EXEMI_AUTOMATION_REDIRECTING = "EXEMI_AUTOMATION_REDIRECTING";
export const EXEMI_CANVAS_TOKEN_RESULT = "EXEMI_CANVAS_TOKEN_RESULT";

export type ExemiAutomationReadyPayload = {
  hashRoute: string;
  isOnboarding: boolean;
  automationResume?: boolean;
};

export type ExemiTokenFailureCode =
  | "NO_NEW_TOKEN_BUTTON"
  | "SCRAPER_TIMEOUT"
  | "TOKEN_NOT_FOUND"
  | "CLOSE_MODAL_FAILED"
  | "FORM_TIMEOUT"
  | "IFRAME_HANDSHAKE_TIMEOUT"
  | "UNKNOWN";

export type ExemiCanvasTokenResultPayload =
  | { ok: true; token: string; universitySubdomain?: string }
  | { ok: false; code: ExemiTokenFailureCode };

export const CANVAS_TOKEN_AUTOMATION_SS_KEY = "exemi_cs_token_automation";

export type CanvasTokenAutomationPhase = "idle" | "redirecting" | "scraping" | "done" | "failed";

export type CanvasTokenAutomationState = {
  phase: CanvasTokenAutomationPhase;
  ts: number;
};
