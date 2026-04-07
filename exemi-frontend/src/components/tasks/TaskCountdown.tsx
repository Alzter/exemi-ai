export type TaskCountdownProps = {
    /** Total session length in seconds (e.g. task duration or break length). */
    totalTimeSeconds: number;
    /** Elapsed seconds within the session (drives the progress arc). */
    progressTimeSeconds: number;
    /** Optional label above the remaining time (e.g. "Focus"). */
    label?: string;
    /** Optional max rendered size in px; defaults to 300. */
    maxSizePx?: number;
};

function formatMmSs(totalSeconds: number): string {
    const s = Math.max(0, Math.floor(totalSeconds));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${String(r).padStart(2, '0')}`;
}

/**
 * Circular countdown: remaining time in the centre; progress ring fills counter-clockwise from 12 o'clock.
 */
export function TaskCountdown({
    totalTimeSeconds,
    progressTimeSeconds,
    label,
    maxSizePx = 300,
}: TaskCountdownProps) {
    const total = Math.max(1, totalTimeSeconds);
    const progressed = Math.max(0, progressTimeSeconds);
    const remaining = Math.max(0, total - progressed);
    const ratio = Math.min(1, progressed / total);

    const r = 52;
    const strokeTrack = 5;
    const strokeProgress = 6;
    const c = 2 * Math.PI * r;
    const dashProgress = ratio * c;

    return (
        <div
            style={{
                position: 'relative',
                width: `min(${maxSizePx}px, 100%)`,
                maxWidth: maxSizePx,
                aspectRatio: '1 / 1',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}
        >
            <svg
                width="100%"
                height="100%"
                viewBox="0 0 128 128"
                aria-hidden
                style={{color: '#1a1a1a', position: 'absolute', inset: 0}}
            >
                <g transform="translate(64,64) rotate(90) scale(-1, 1)">
                    <circle
                        r={r}
                        cx={0}
                        cy={0}
                        fill="none"
                        stroke="rgba(0,0,0,0.12)"
                        strokeWidth={strokeTrack}
                    />
                    {progressTimeSeconds > 0 ? 
                        <circle
                            r={r}
                            cx={0}
                            cy={0}
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={strokeProgress}
                            strokeLinecap="round"
                            strokeDasharray={`${dashProgress} ${c}`}
                        />
                    : null}
                </g>
            </svg>
            <div
                style={{
                    position: 'relative',
                    zIndex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    pointerEvents: 'none',
                    textAlign: 'center',
                }}
            >
                {label ? (
                    <span style={{fontSize: 'clamp(0.65rem, 2.7vw, 1rem)', fontWeight: 700, opacity: 0.75, marginBottom: 2}}>
                        {label}
                    </span>
                ) : null}
                <span style={{fontSize: 'clamp(1.6rem, 10vw, 3rem)', fontWeight: 800, letterSpacing: '-0.02em'}}>
                    {formatMmSs(remaining)}
                </span>
            </div>
        </div>
    );
}
