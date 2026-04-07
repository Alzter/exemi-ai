import {useEffect, useState} from 'react';
import {MdKeyboardArrowDown, MdKeyboardArrowUp, MdTimer} from 'react-icons/md';
import {DialogBox} from '../ui/DialogBox';

const MIN_MINS = 5;
const MAX_MINS = 60;
const STEP = 5;
const DEFAULT_MINS = 15;

export type TaskBreakSetupProps = {
    open: boolean;
    onClose: () => void;
    onConfirmBreak: (durationMinutes: number) => void;
};

export function TaskBreakSetup({open, onClose, onConfirmBreak}: TaskBreakSetupProps) {
    const [mins, setMins] = useState(DEFAULT_MINS);

    useEffect(() => {
        if (open) setMins(DEFAULT_MINS);
    }, [open]);

    const bump = (delta: number) => {
        setMins((m) => {
            const n = m + delta;
            return Math.min(MAX_MINS, Math.max(MIN_MINS, Math.round(n / STEP) * STEP || MIN_MINS));
        });
    };

    return (
        <DialogBox
            open={open}
            onClose={onClose}
            backdropClassName="dialog-backdrop--elevated"
            aria-label="Break time setup"
            panelClassName="task-edit-dialog-panel"
            panelStyle={{
                width: 'min(420px, calc(100vw - 2rem))',
                borderRadius: 8,
                backgroundColor: '#ececec',
                color: '#1a1a1a',
            }}
        >
            <div className="dialog-panel-title">
                <h3>Break time</h3>
            </div>
            <div className="dialog-panel-body">
                <p style={{margin: 0, fontWeight: 500}}>How long would you like to take a break for?</p>
                <div
                    className="input-row"
                    style={{
                        alignItems: 'center',
                        minHeight: 48,
                        height: 'auto',
                        border: '2px solid rgba(0,0,0,0.14)',
                        borderRadius: 8,
                        padding: '6px 10px',
                        boxSizing: 'border-box',
                        background: '#fff',
                    }}
                >
                    <MdTimer aria-hidden style={{fontSize: 28, flexShrink: 0, opacity: 0.75}} />
                    <span style={{flex: 1, fontWeight: 700, paddingLeft: 8}}>
                        {mins} minute{mins === 1 ? '' : 's'}
                    </span>
                    <div style={{display: 'flex', flexDirection: 'column', gap: 2}}>
                        <button
                            type="button"
                            className="floating"
                            aria-label="Increase break length"
                            style={{width: 36, height: 32}}
                            onClick={() => bump(STEP)}
                            disabled={mins >= MAX_MINS}
                        >
                            <MdKeyboardArrowUp aria-hidden />
                        </button>
                        <button
                            type="button"
                            className="floating"
                            aria-label="Decrease break length"
                            style={{width: 36, height: 32}}
                            onClick={() => bump(-STEP)}
                            disabled={mins <= MIN_MINS}
                        >
                            <MdKeyboardArrowDown aria-hidden />
                        </button>
                    </div>
                </div>
                <button type="button" className="primary" onClick={() => onConfirmBreak(mins)}>
                    Take a break
                </button>
            </div>
        </DialogBox>
    );
}
