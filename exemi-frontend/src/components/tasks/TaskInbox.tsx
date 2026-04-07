import {useCallback, useRef, useState} from 'react';
import {MdAdd, MdChevronLeft, MdClose, MdDelete} from 'react-icons/md';
import {safeTaskBackgroundFromColourRaw} from '../../utils/taskBoardUtils';

export type TaskInboxItem = {
    tempId: number;
    name: string;
};

export type TaskInboxProps = {
    items: TaskInboxItem[];
    onItemsChange: (next: TaskInboxItem[]) => void;
    isBoardWideViewport: boolean;
};

export function TaskInbox({items, onItemsChange, isBoardWideViewport}: TaskInboxProps) {
    const [draft, setDraft] = useState('');
    const [minimized, setMinimized] = useState(false);
    const tempIdRef = useRef(0);
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

    if (minimized) {
        return (
            <div
                style={{
                    borderLeft: '2px solid rgba(0,0,0,0.12)',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    padding: '8px 4px',
                    minWidth: 44,
                    background: 'rgba(255,255,255,0.35)',
                }}
            >
                <button
                    type="button"
                    className="floating"
                    aria-label="Expand New Tasks"
                    onClick={() => setMinimized(false)}
                >
                    <MdChevronLeft aria-hidden style={{transform: 'rotate(180deg)'}} />
                </button>
                <span
                    style={{
                        writingMode: 'vertical-rl',
                        transform: 'rotate(180deg)',
                        fontSize: '0.75rem',
                        fontWeight: 800,
                        marginTop: 12,
                        letterSpacing: '0.04em',
                    }}
                >
                    New Tasks
                </span>
            </div>
        );
    }

    return (
        <div
            style={{
                borderLeft: '2px solid rgba(0,0,0,0.12)',
                display: 'flex',
                flexDirection: 'column',
                width: 'min(300px, 34vw)',
                maxWidth: 320,
                minWidth: 200,
                background: 'rgba(255,255,255,0.35)',
                minHeight: 0,
            }}
        >
            <div
                style={{
                    display: 'flex',
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 10px 6px',
                    gap: 8,
                }}
            >
                <h4 style={{margin: 0, fontSize: '1em', fontWeight: 800}}>New Tasks</h4>
                <button
                    type="button"
                    className="floating"
                    aria-label="Minimise New Tasks"
                    onClick={() => setMinimized(true)}
                >
                    <MdClose aria-hidden />
                </button>
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
            <div style={{padding: '8px 10px 12px', display: 'flex', flexDirection: 'column', gap: 8}}>
                <input
                    type="text"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            addItem();
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
                        onClick={addItem}
                        aria-label="Add inbox task"
                    >
                        <MdAdd aria-hidden />
                        <span>Add</span>
                    </button>
                    <button
                        type="button"
                        className="tasks-panel-task-entry-cancel"
                        aria-label="Clear inbox task name"
                        onClick={() => setDraft('')}
                    >
                        <MdClose aria-hidden />
                    </button>
                </div>
            </div>
        </div>
    );
}
