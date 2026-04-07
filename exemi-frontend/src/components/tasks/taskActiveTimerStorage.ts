const STORAGE_KEY = 'exemi.activeTaskTimer.v1';

export type ActiveTaskTimerPersistV1 = {
    v: 1;
    username: string;
    taskId: number;
    progress_secs: number;
    foreground: boolean;
    selectedDateISO: string;
};

function parse(raw: string | null): ActiveTaskTimerPersistV1 | null {
    if (raw == null || raw === '') return null;
    try {
        const o = JSON.parse(raw) as unknown;
        if (!o || typeof o !== 'object') return null;
        const r = o as Record<string, unknown>;
        if (r.v !== 1) return null;
        if (typeof r.username !== 'string' || r.username === '') return null;
        if (typeof r.taskId !== 'number' || !Number.isFinite(r.taskId)) return null;
        if (typeof r.progress_secs !== 'number' || !Number.isFinite(r.progress_secs)) return null;
        if (typeof r.foreground !== 'boolean') return null;
        if (typeof r.selectedDateISO !== 'string' || r.selectedDateISO === '') return null;
        return {
            v: 1,
            username: r.username,
            taskId: r.taskId,
            progress_secs: Math.max(0, Math.floor(r.progress_secs)),
            foreground: r.foreground,
            selectedDateISO: r.selectedDateISO,
        };
    } catch {
        return null;
    }
}

export function readActiveTaskTimer(): ActiveTaskTimerPersistV1 | null {
    if (typeof localStorage === 'undefined') return null;
    try {
        return parse(localStorage.getItem(STORAGE_KEY));
    } catch {
        return null;
    }
}

export function writeActiveTaskTimer(p: ActiveTaskTimerPersistV1): void {
    if (typeof localStorage === 'undefined') return;
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
    } catch {
        /* quota / private mode */
    }
}

export function clearActiveTaskTimer(): void {
    if (typeof localStorage === 'undefined') return;
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch {
        /* ignore */
    }
}
