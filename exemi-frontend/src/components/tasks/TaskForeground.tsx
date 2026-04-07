import {useState} from 'react';
import {MdCheck, MdClose} from 'react-icons/md';
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
    const [inboxMinimized, setInboxMinimized] = useState(true);
    if (!task) return null;

    const totalSecs = Math.max(60, task.duration_mins * 60);
    const foregroundWidth = inboxMinimized ? 'calc(100% - 72px)' : 'calc(100% - min(300px, 60%))';
    const inboxWidth = inboxMinimized ? '72px' : 'min(300px, 60%)';

    return (
        <DialogBox
            open={open}
            onClose={onPauseToBackground}
            closeOnEscape={false}
            showCloseButton={false}
            backdropClassName="dialog-backdrop--elevated dialog-backdrop--task-foreground"
            aria-label="Focus on task"
            panelStyle={{
                width: 'min(920px, calc(100vw - 1.5rem))',
                maxHeight: 'min(90vh, 880px)',
                borderRadius: 8,
                background: 'transparent',
                border: 'none',
                boxShadow: 'none',
                overflow: 'visible',
                padding: 0,
            }}
        >
            <div
                style={{
                    position: 'relative',
                    width: '100%',
                    height: 'min(90vh, 880px)',
                    display: 'grid',
                    gridTemplateColumns: `${foregroundWidth} ${inboxWidth}`,
                    gap: 0,
                    transition: 'grid-template-columns 0.2s ease-in-out',
                }}
            >
                <div
                    className="task-edit-dialog-panel"
                    style={{
                        position: 'relative',
                        zIndex: 2,
                        backgroundColor: panelBackgroundColor,
                        color: '#1a1a1a',
                        display: 'flex',
                        flexDirection: 'column',
                        border: '2px solid rgba(0, 0, 0, 0.14)',
                        boxShadow: '0 4px 4px rgba(0, 0, 0, 0.12)',
                        borderRadius: '8px 0 0 8px',
                        transition: 'width 0.2s ease-in-out',
                        width: '100%',
                        minWidth: 0,
                        overflow: 'hidden',
                    }}
                >
                    <div
                        className="dialog-panel-top-actions"
                        style={{
                            position: 'absolute',
                            top: 14,
                            right: 14,
                            zIndex: 3,
                            display: 'inline-flex',
                            flexDirection: 'row',
                            alignItems: 'center',
                        }}
                    >
                        <button
                            type="button"
                            className="floating"
                            aria-label="Pause and switch to background mode"
                            onClick={onPauseToBackground}
                        >
                            <MdClose aria-hidden />
                        </button>
                    </div>
                    <div
                        className="dialog-panel-title"
                        style={{
                            marginRight: 'calc(56px + 14px)',
                            height: 'auto',
                            minHeight: 40,
                            alignItems: 'flex-start'
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
                                flex: '1 1 auto',
                                minWidth: 0,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'stretch',
                                padding: '8px 14px 14px',
                                gap: 16,
                            }}
                        >
                            <div
                                style={{
                                    flex: 1,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
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
                    </div>
                </div>
                <div
                    style={{
                        zIndex: 1,
                        borderRadius: 8,
                        borderTopLeftRadius: 0,
                        borderBottomLeftRadius: 0,
                        border: '2px solid rgba(0, 0, 0, 0.14)',
                        boxShadow: '0 4px 4px rgba(0, 0, 0, 0.12)',
                        backgroundColor: panelBackgroundColor,
                        filter: inboxMinimized ? 'brightness(0.8)' : 'none',
                        transition: 'width 0.2s ease-in-out, filter 0.2s ease-in-out, background-color 0.2s ease-in-out',
                        width: '100%',
                        minWidth: 0,
                        overflow: 'hidden',
                        position: 'relative',
                    }}
                >
                    <TaskInbox
                        items={inboxItems}
                        onItemsChange={onInboxItemsChange}
                        isBoardWideViewport={isBoardWideViewport}
                        minimized={inboxMinimized}
                        onToggleMinimized={() => setInboxMinimized((v) => !v)}
                    />
                </div>
            </div>
        </DialogBox>
    );
}
