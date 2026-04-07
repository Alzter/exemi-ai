import {MdCheck, MdPause} from 'react-icons/md';
import {DialogBox} from '../ui/DialogBox';
import {TaskCountdown} from './TaskCountdown';
import {TaskInbox, type TaskInboxItem} from './TaskInbox';

type TaskLite = {
    id: number;
    name: string;
    duration_mins: number;
    colour_raw: string | null;
};

export type TaskForegroundProps = {
    open: boolean;
    /** Escape / backdrop uses the same handler as pause (flush + background). */
    onPauseToBackground: () => void;
    task: TaskLite | null;
    panelBackgroundColor: string;
    /** progress_secs plus any client-side seconds since the timer resumed. */
    progressSecondsEffective: number;
    inboxItems: TaskInboxItem[];
    onInboxItemsChange: (next: TaskInboxItem[]) => void;
    isBoardWideViewport: boolean;
    onNeedHelp: () => void;
    onFinished: () => void;
};

export function TaskForeground({
    open,
    onPauseToBackground,
    task,
    panelBackgroundColor,
    progressSecondsEffective,
    inboxItems,
    onInboxItemsChange,
    isBoardWideViewport,
    onNeedHelp,
    onFinished,
}: TaskForegroundProps) {
    if (!task) return null;

    const totalSecs = Math.max(60, task.duration_mins * 60);

    return (
        <DialogBox
            open={open}
            onClose={onPauseToBackground}
            closeOnEscape
            showCloseButton={false}
            backdropClassName="dialog-backdrop--elevated dialog-backdrop--task-foreground"
            beforeClose={
                <button
                    type="button"
                    className="floating"
                    aria-label="Pause and switch to background mode"
                    onClick={onPauseToBackground}
                >
                    <MdPause aria-hidden />
                </button>
            }
            aria-label="Focus on task"
            panelClassName="task-edit-dialog-panel"
            panelStyle={{
                width: 'min(920px, calc(100vw - 1.5rem))',
                maxHeight: 'min(90vh, 880px)',
                borderRadius: 8,
                backgroundColor: panelBackgroundColor,
                color: '#1a1a1a',
                display: 'flex',
                flexDirection: 'column',
            }}
        >
            <div
                className="dialog-panel-title"
                style={{
                    marginRight: 'calc(56px + 14px)',
                    height: 'auto',
                    minHeight: 40,
                    alignItems: 'flex-start',
                    whiteSpace: 'normal',
                }}
            >
                <h3 style={{whiteSpace: 'normal', lineHeight: 1.25}}>{task.name}</h3>
            </div>
            <div
                className="dialog-panel-body"
                style={{
                    flex: 1,
                    minHeight: 0,
                    display: 'flex',
                    flexDirection: 'row',
                    padding: 0,
                    gap: 0,
                }}
            >
                <div
                    style={{
                        flex: '1 1 58%',
                        minWidth: 0,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'stretch',
                        padding: '8px 14px 14px',
                        gap: 16,
                    }}
                >
                    <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                        <TaskCountdown
                            totalTimeSeconds={totalSecs}
                            progressTimeSeconds={progressSecondsEffective}
                            label="Focus"
                        />
                    </div>
                    <div className="double-column-buttons" style={{marginTop: 'auto'}}>
                        <button type="button" className="secondary" onClick={onNeedHelp}>
                            I need help
                        </button>
                        <button type="button" className="primary" onClick={onFinished}>
                            <MdCheck aria-hidden />
                            I finished it
                        </button>
                    </div>
                </div>
                <TaskInbox
                    items={inboxItems}
                    onItemsChange={onInboxItemsChange}
                    isBoardWideViewport={isBoardWideViewport}
                />
            </div>
        </DialogBox>
    );
}
