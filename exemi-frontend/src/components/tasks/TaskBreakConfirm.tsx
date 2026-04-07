import {DialogBox} from '../ui/DialogBox';
import {safeTaskBackgroundFromColourRaw} from '../../utils/taskBoardUtils';

export type NextTaskPreview = {
    id: number;
    name: string;
    duration_mins: number;
    colour_raw: string | null;
};

export type TaskBreakConfirmProps = {
    open: boolean;
    onClose: () => void;
    completedCount: number;
    nextTask: NextTaskPreview | null;
    isBoardWideViewport: boolean;
    onTakeBreak: () => void;
    onKeepGoing: () => void;
};

export function TaskBreakConfirm({
    open,
    onClose,
    completedCount,
    nextTask,
    isBoardWideViewport,
    onTakeBreak,
    onKeepGoing,
}: TaskBreakConfirmProps) {
    const durLabel = nextTask
        ? isBoardWideViewport
            ? `${nextTask.duration_mins} minute${nextTask.duration_mins === 1 ? '' : 's'}`
            : `${nextTask.duration_mins} min`
        : '';

    return (
        <DialogBox
            open={open}
            onClose={onClose}
            backdropClassName="dialog-backdrop--elevated"
            aria-label="Task complete"
            panelClassName="task-edit-dialog-panel"
            panelStyle={{
                width: 'min(480px, calc(100vw - 2rem))',
                borderRadius: 8,
                backgroundColor: '#ececec',
                color: '#1a1a1a',
            }}
        >
            <div className="dialog-panel-title">
                <h3>
                    Great job! {completedCount} task{completedCount === 1 ? '' : 's'} complete
                </h3>
            </div>
            <div className="dialog-panel-body">
                {nextTask ? (
                    <>
                        <p style={{margin: 0, fontWeight: 500}}>
                            Would you like to continue with the next task or take a break?
                        </p>
                        <div
                            className="tasks-panel-task-row"
                            style={{
                                backgroundColor: safeTaskBackgroundFromColourRaw(nextTask.colour_raw),
                                cursor: 'default',
                                marginTop: 4,
                            }}
                        >
                            <div className="tasks-panel-task-name-outer">
                                <span className="tasks-panel-task-name-inner">{nextTask.name}</span>
                            </div>
                            <span className="tasks-panel-task-duration">{durLabel}</span>
                        </div>
                        <div className="double-column-buttons" style={{marginTop: 12}}>
                            <button type="button" className="secondary" onClick={onTakeBreak}>
                                Take a break
                            </button>
                            <button
                                type="button"
                                className="primary"
                                onClick={onKeepGoing}
                            >
                                Keep going
                            </button>
                        </div>
                    </>
                ) : (
                    <>
                        <p>
                            You completed all your tasks for today!
                        </p>
                        <button
                            type="button"
                            className="primary"
                            onClick={onClose}
                        >
                            OK
                        </button>
                    </>
                )}
            </div>
        </DialogBox>
    );
}
