import {useCallback, useEffect, useRef, useState} from 'react';
import {MdAdd, MdClose, MdDelete} from 'react-icons/md';
import {safeTaskBackgroundFromColourRaw} from '../../utils/taskBoardUtils';

export type TaskInboxItem = {
    tempId: number;
    name: string;
};

export type TaskInboxProps = {
    items: TaskInboxItem[];
    onItemsChange: (next: TaskInboxItem[]) => void;
    isBoardWideViewport: boolean;
    minimized: boolean;
    onToggleMinimized: () => void;
};

export function TaskInbox({
    items,
    onItemsChange,
    isBoardWideViewport,
    minimized,
    onToggleMinimized,
}: TaskInboxProps) {
    const [draft, setDraft] = useState('');
    const [taskEntryOpen, setTaskEntryOpen] = useState(false);
    const tempIdRef = useRef(0);
    const entryInputRef = useRef<HTMLInputElement>(null);
    const neutralBg = safeTaskBackgroundFromColourRaw(null);

    const addItem = useCallback(() => {
        const name = draft.trim();
        if (!name) return;
        const tempId = --tempIdRef.current;
        onItemsChange([...items, {tempId, name}]);
        setDraft('');
    }, [draft, items, onItemsChange]);

    const removeItem = useCallback(
        (tempId: number) => {
            onItemsChange(items.filter((x) => x.tempId !== tempId));
        },
        [items, onItemsChange],
    );

    const cancelTaskEntry = useCallback(() => {
        setTaskEntryOpen(false);
        setDraft('');
    }, []);

    const confirmTaskEntry = useCallback(() => {
        addItem();
        setTaskEntryOpen(false);
    }, [addItem]);

    useEffect(() => {
        if (!taskEntryOpen || minimized) return;
        entryInputRef.current?.focus();
    }, [taskEntryOpen, minimized]);

    return (
        <div
            style={{
                display: 'flex',
                flexDirection: 'column',
                width: '100%',
                minHeight: 0,
                height: '100%',
            }}
        >
            <div className="dialog-panel-top-actions">
                <button
                    type="button"
                    className="floating"
                    aria-label={minimized ? 'Expand New Tasks' : 'Minimise New Tasks'}
                    onClick={onToggleMinimized}
                >
                    {minimized ? (
                        <MdAdd aria-hidden />
                    ) : (
                        <MdClose aria-hidden />
                    )}
                </button>
            </div>
            <div
                style={{
                    display: 'flex',
                    flexDirection: 'column',
                    flex: '1 1 auto',
                    minHeight: 0,
                    opacity: minimized ? 0 : 1,
                    transition: 'opacity 0.2s ease-in-out',
                    pointerEvents: minimized ? 'none' : 'auto',
                }}
            >
                <div
                    className="dialog-panel-title"
                >
                    <h3>New Tasks</h3>
                </div>
                <div
                    style={{
                        flex: '1 1 auto',
                        overflowY: 'auto',
                        padding: '0 10px 8px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 8,
                        minHeight: 120,
                    }}
                >
                    {items.map((t) => {
                        const durLabel = isBoardWideViewport ? '15 minutes' : '15 min';
                        return (
                            <div
                                key={t.tempId}
                                className="tasks-panel-task-row"
                                style={{
                                    backgroundColor: neutralBg,
                                    cursor: 'default',
                                }}
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="tasks-panel-task-name-outer">
                                    <span className="tasks-panel-task-name-inner">{t.name}</span>
                                </div>
                                <span className="tasks-panel-task-duration">{durLabel}</span>
                                <button
                                    type="button"
                                    className="floating"
                                    aria-label={`Remove ${t.name}`}
                                    style={{width: 36, height: 36, flexShrink: 0}}
                                    onClick={() => removeItem(t.tempId)}
                                >
                                    <MdDelete aria-hidden />
                                </button>
                            </div>
                        );
                    })}
                </div>
                <div
                    style={{
                        flexShrink: 0,
                        padding: '14px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 8,
                    }}
                >
                    {taskEntryOpen ? (
                        <>
                            <input
                                ref={entryInputRef}
                                type="text"
                                value={draft}
                                onChange={(e) => setDraft(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        e.preventDefault();
                                        if (draft.trim()) confirmTaskEntry();
                                    }
                                    if (e.key === 'Escape') {
                                        e.preventDefault();
                                        cancelTaskEntry();
                                    }
                                }}
                                placeholder="Task name"
                                aria-label="New inbox task name"
                                className="tasks-panel-task-entry-input"
                                style={{width: '100%', boxSizing: 'border-box'}}
                            />
                            <div className="tasks-panel-task-entry-actions" style={{width: '100%'}}>
                                <button
                                    type="button"
                                    className="secondary"
                                    disabled={!draft.trim()}
                                    onClick={confirmTaskEntry}
                                    aria-label="Add inbox task"
                                >
                                    <MdAdd aria-hidden />
                                    <span>Add</span>
                                </button>
                                <button
                                    type="button"
                                    className="tasks-panel-task-entry-cancel"
                                    aria-label="Cancel adding inbox task"
                                    onClick={cancelTaskEntry}
                                >
                                    <MdClose aria-hidden />
                                </button>
                            </div>
                        </>
                    ) : (
                        <button type="button" className="secondary" onClick={() => setTaskEntryOpen(true)}>
                            <MdAdd aria-hidden />
                            Add Task
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
