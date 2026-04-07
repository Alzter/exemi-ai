/** UTC ISO instant where `calendarDate` (YYYY-MM-DD) is that local calendar day in `timeZone`. */
export function utcIsoForLocalCalendarDate(calendarDate: string, timeZone: string): string {
    const [y, m, d] = calendarDate.split('-').map(Number);
    if (!y || !m || !d) return new Date().toISOString();

    let t = Date.UTC(y, m - 1, d, 12, 0, 0);
    for (let i = 0; i < 48; i++) {
        const date = new Date(t);
        const parts = new Intl.DateTimeFormat('en-CA', {
            timeZone,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        }).formatToParts(date);
        const py = Number(parts.find((p) => p.type === 'year')?.value);
        const pm = Number(parts.find((p) => p.type === 'month')?.value);
        const pd = Number(parts.find((p) => p.type === 'day')?.value);
        if (py === y && pm === m && pd === d) {
            return date.toISOString();
        }
        const cmp = py !== y ? py - y : pm !== m ? pm - m : pd - d;
        t += (cmp > 0 ? -1 : 1) * 3600000;
    }
    return new Date(Date.UTC(y, m - 1, d, 12, 0, 0)).toISOString();
}

function srgbChannelToLinear(c: number): number {
    const x = c / 255;
    return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
}

function linearSrgbToOklab(r: number, g: number, b: number): {L: number; a: number; b: number} {
    const l = 0.412_221_4708 * r + 0.536_332_5363 * g + 0.051_445_9929 * b;
    const m = 0.211_903_4982 * r + 0.680_699_5451 * g + 0.107_396_9566 * b;
    const s = 0.088_302_4619 * r + 0.281_718_8376 * g + 0.629_978_7005 * b;
    const l_ = Math.cbrt(l);
    const m_ = Math.cbrt(m);
    const s_ = Math.cbrt(s);
    return {
        L: 0.210_454_2553 * l_ + 0.793_617_785 * m_ - 0.004_072_0468 * s_,
        a: 1.977_998_4951 * l_ - 2.428_592_205 * m_ + 0.450_593_7099 * s_,
        b: 0.025_904_0371 * l_ + 0.782_771_7662 * m_ - 0.808_675_766 * s_,
    };
}

function oklabToHueDegrees(a: number, b: number): number {
    let h = (Math.atan2(b, a) * 180) / Math.PI;
    if (h < 0) h += 360;
    return h;
}

const SAFE_L = 0.92;
const SAFE_C = 0.036;
const NEUTRAL_H = 260;


/** Parse backend `colour_raw` (e.g. RRGGBB or #RRGGBB); return OKLCH CSS color with fixed L/C and preserved hue. */
export function parseColourRawToOklch(colourRaw: string, luminanceOverride : number = 0.92, chromaOverride : number = 0.036): string{
    if (!colourRaw || typeof colourRaw !== 'string') {
        return `oklch(${SAFE_L} ${SAFE_C * 0.55} ${NEUTRAL_H})`;
    }
    const hex = colourRaw.replace(/^#/, '').trim();
    if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
        return `oklch(${SAFE_L} ${SAFE_C * 0.55} ${NEUTRAL_H})`;
    }
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const lr = srgbChannelToLinear(r);
    const lg = srgbChannelToLinear(g);
    const lb = srgbChannelToLinear(b);
    const lab = linearSrgbToOklab(lr, lg, lb);
    const chroma = chromaOverride ? chromaOverride : Math.hypot(lab.a, lab.b);
    const luminance = luminanceOverride ? luminanceOverride : SAFE_L;
    const h = chroma < 1e-6 ? NEUTRAL_H : oklabToHueDegrees(lab.a, lab.b);
    return `oklch(${luminance} ${chroma} ${h.toFixed(2)})`;
}

/** Parse backend `colour_raw` (e.g. RRGGBB or #RRGGBB); return OKLCH CSS color with fixed L/C and preserved hue. */
export function safeTaskBackgroundFromColourRaw(colourRaw: string | null | undefined): string {
    if (!colourRaw || typeof colourRaw !== 'string') {
        return `oklch(${SAFE_L} ${SAFE_C * 0.55} ${NEUTRAL_H})`;
    }
    const hex = colourRaw.replace(/^#/, '').trim();
    if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
        return `oklch(${SAFE_L} ${SAFE_C * 0.55} ${NEUTRAL_H})`;
    }
    const r = parseInt(hex.slice(0, 2), 16);
    const g = parseInt(hex.slice(2, 4), 16);
    const b = parseInt(hex.slice(4, 6), 16);
    const lr = srgbChannelToLinear(r);
    const lg = srgbChannelToLinear(g);
    const lb = srgbChannelToLinear(b);
    const lab = linearSrgbToOklab(lr, lg, lb);
    const chroma = Math.hypot(lab.a, lab.b);
    const h = chroma < 1e-6 ? NEUTRAL_H : oklabToHueDegrees(lab.a, lab.b);
    return `oklch(${SAFE_L} ${SAFE_C} ${h.toFixed(2)})`;
}

/** Same hue/chroma; lightness reduced by 20% for completed tasks. */
export function completedTaskBackgroundFromSafe(safeCss: string): string {
    const m = safeCss.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/i);
    if (!m) return safeCss;
    const L = Number(m[1]);
    const c = Number(m[2]);
    const h = m[3];
    const L2 = Math.max(0, L * 0.8);
    return `oklch(${L2} ${c} ${h})`;
}

/** Stronger chroma and slightly lower L than the soft task tile colour — for in-progress bar fill. */
export function saturatedProgressBarFromSafe(safeCss: string): string {
    const m = safeCss.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/i);
    if (!m) return 'oklch(0.72 0.14 95)';
    const L = Number(m[1]);
    const c = Number(m[2]);
    const h = m[3];
    const c2 = Math.min(0.19, Math.max(c * 4, c + 0.06));
    const L2 = Math.max(0.58, Math.min(0.82, L - 0.14));
    return `oklch(${L2} ${c2} ${h})`;
}
/** Stronger chroma and slightly lower L than the soft task tile colour — for in-progress bar border. */
export function saturatedProgressBarBorderFromSafe(safeCss: string): string {
    const m = safeCss.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/i);
    if (!m) return 'oklch(0.5 0.14 95)';
    const L = Number(m[1]);
    const c = Number(m[2]);
    const h = m[3];
    const c2 = Math.min(0.19, Math.max(c * 4, c + 0.06));
    const L2 = Math.max(0.4, Math.min(0.82, L - 0.4));
    return `oklch(${L2} ${c2} ${h})`;
}