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
                <div className="task-break-setup-duration-row">
                    <MdTimer aria-hidden className="task-break-setup-duration-icon" />
                    <span className="task-break-setup-duration-label">
                        {mins} minute{mins === 1 ? '' : 's'}
                    </span>
                    <div className="task-break-bump-stack">
                        <button
                            type="button"
                            className="task-break-bump-btn"
                            aria-label="Increase break length"
                            onClick={() => bump(STEP)}
                            disabled={mins >= MAX_MINS}
                        >
                            <MdKeyboardArrowUp aria-hidden />
                        </button>
                        <button
                            type="button"
                            className="task-break-bump-btn"
                            aria-label="Decrease break length"
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
