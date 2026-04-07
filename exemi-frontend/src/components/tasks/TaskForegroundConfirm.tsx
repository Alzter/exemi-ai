import {DialogBox} from '../ui/DialogBox';
import {TaskCountdown} from './TaskCountdown';

export type TaskForegroundConfirmProps = {
    open: boolean;
    onClose: () => void;
    /** Same surface treatment as the task edit dialog. */
    panelBackgroundColor: string;
    taskDurationMins: number;
    taskProgressSecs: number;
    onChooseBackground: () => void;
    onChooseForeground: () => void;
};

export function TaskForegroundConfirm({
    open,
    onClose,
    panelBackgroundColor,
    taskDurationMins,
    taskProgressSecs,
    onChooseBackground,
    onChooseForeground,
}: TaskForegroundConfirmProps) {
    const totalSecs = Math.max(60, taskDurationMins * 60);

    return (
        <DialogBox
            open={open}
            onClose={onClose}
            closeOnEscape={false}
            backdropClassName="dialog-backdrop--elevated"
            aria-label="Use focus timer"
            panelClassName="task-edit-dialog-panel"
            panelStyle={{
                width: 'min(420px, calc(100vw - 2rem))',
                borderRadius: 8,
                backgroundColor: panelBackgroundColor,
                color: '#1a1a1a',
            }}
        >
            <div className="dialog-panel-title">
                <h3>Use focus timer?</h3>
            </div>
            <div className="dialog-panel-body" style={{paddingTop: 4}}>
                <p style={{margin: 0, fontWeight: 500, lineHeight: 1.45}}>
                    Would you like to <strong>remove distractions</strong> while working on this task?
                </p>
                <div style={{display: 'flex', justifyContent: 'center', margin: '8px 0 4px'}}>
                    <TaskCountdown
                        totalTimeSeconds={totalSecs}
                        progressTimeSeconds={0}
                        label="Focus"
                    />
                </div>
                <div className="double-column-buttons" style={{marginTop: 8}}>
                    <button type="button" className="secondary" onClick={onChooseBackground}>
                        No
                    </button>
                    <button type="button" className="primary" onClick={onChooseForeground}>
                        Yes
                    </button>
                </div>
            </div>
        </DialogBox>
    );
}
