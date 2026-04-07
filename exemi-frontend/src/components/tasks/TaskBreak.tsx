import {useEffect, useState} from 'react';
import {DialogBox} from '../ui/DialogBox';
import {TaskCountdown} from './TaskCountdown';

export type TaskBreakProps = {
    open: boolean;
    onClose: () => void;
    durationSeconds: number;
    onNextTask: () => void;
};

export function TaskBreak({open, onClose, durationSeconds, onNextTask}: TaskBreakProps) {
    const [elapsed, setElapsed] = useState(0);

    useEffect(() => {
        if (!open) {
            setElapsed(0);
            return;
        }
        setElapsed(0);
        const id = window.setInterval(() => {
            setElapsed((e) => e + 1);
        }, 1000);
        return () => window.clearInterval(id);
    }, [open, durationSeconds]);

    const total = Math.max(1, durationSeconds);

    return (
        <DialogBox
            open={open}
            onClose={onClose}
            backdropClassName="dialog-backdrop--elevated"
            aria-label="Break timer"
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
            <div className="dialog-panel-body" style={{alignItems: 'center', minHeight: 0}}>
                <div
                    style={{
                        width: '100%',
                        flex: 1,
                        minHeight: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '4px 0 8px',
                    }}
                >
                    <TaskCountdown
                        totalTimeSeconds={total}
                        progressTimeSeconds={elapsed}
                    />
                </div>
                <button type="button" className="secondary" onClick={onNextTask}>
                    Next task
                </button>
            </div>
        </DialogBox>
    );
}
