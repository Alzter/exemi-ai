import {useCallback, useEffect, useRef, useState, type RefObject} from 'react';
import {
    MdArrowLeft,
    MdArrowRight,
    MdCheckBox,
    MdCheckBoxOutlineBlank,
    MdKeyboardArrowDown,
    MdKeyboardArrowUp,
    MdRefresh,
} from 'react-icons/md';
import {type Session} from '../../models';
import {
    completedTaskBackgroundFromSafe,
    safeTaskBackgroundFromColourRaw,
    utcIsoForLocalCalendarDate,
} from '../../utils/taskBoardUtils';

const backendURL = import.meta.env.VITE_BACKEND_API_URL;

function formatISODateLocal(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function parseISODateLocal(iso: string): Date {
    const [y, m, d] = iso.split('-').map(Number);
    return new Date(y, m - 1, d);
}

function calendarDaysBetween(isoA: string, isoB: string): number {
    const a = parseISODateLocal(isoA).getTime();
    const b = parseISODateLocal(isoB).getTime();
    return Math.round((a - b) / 86400000);
}

function formatTaskHeaderDateLabel(selectedISO: string, todayISOValue: string): string {
    if (selectedISO === todayISOValue) return 'Today';
    const delta = calendarDaysBetween(selectedISO, todayISOValue);
    if (delta === -1) return 'Yesterday';
    if (delta === 1) return 'Tomorrow';
    const d = parseISODateLocal(selectedISO);
    return d.toLocaleDateString('en-GB', {weekday: 'long', day: 'numeric', month: 'long'});
}

const COLLAPSED_PX = 52;
const MIN_EXPANDED_PX = 160;
/** Default height when expanding before the user has resized (50% of viewport). */
const DEFAULT_EXPANDED_VIEWPORT_RATIO = 0.5;
const MAX_VIEWPORT_RATIO = 0.78;

const BOARD_WIDE_BREAKPOINT_MQ = '(min-width: 600px)';

function getDefaultExpandedHeightPx(): number {
    if (typeof window === 'undefined') return MIN_EXPANDED_PX;
    return window.innerHeight * DEFAULT_EXPANDED_VIEWPORT_RATIO;
}

function clamp(n: number, lo: number, hi: number) {
    return Math.min(hi, Math.max(lo, n));
}

type TaskPublicRow = {
    id: number;
    name: string;
    duration_mins: number;
    completed: boolean;
    colour_raw: string | null;
};

type TasksWindowProps = {
    session: Session;
    layoutContainerRef: RefObject<HTMLDivElement | null>;
};

export default function TasksWindow({session, layoutContainerRef}: TasksWindowProps) {
    const lastExpandedRef = useRef(getDefaultExpandedHeightPx());
    const [heightPx, setHeightPx] = useState(COLLAPSED_PX);
    const [dragging, setDragging] = useState(false);
    const [selectedDateISO, setSelectedDateISO] = useState(() => formatISODateLocal(new Date()));
    const [isBoardWideViewport, setIsBoardWideViewport] = useState(() => {
        if (typeof window === 'undefined') return true;
        return window.matchMedia(BOARD_WIDE_BREAKPOINT_MQ).matches;
    });

    const [tasks, setTasks] = useState<TaskPublicRow[]>([]);
    const [tasksLoading, setTasksLoading] = useState(false);
    const [tasksError, setTasksError] = useState<string | null>(null);

    const dragStartY = useRef(0);
    const dragStartHeight = useRef(0);
    const activePointerId = useRef<number | null>(null);

    const open = heightPx > COLLAPSED_PX + 1;

    const todayISOValue = formatISODateLocal(new Date());
    const dateLabel = formatTaskHeaderDateLabel(selectedDateISO, todayISOValue);
    const showResetDate = selectedDateISO !== todayISOValue;

    const showTodoColumn = selectedDateISO >= todayISOValue;
    /** Wide: show Done with To-Do for today. Narrow: show Done only for past days (To-Do hidden). */
    const showDoneColumn =
        selectedDateISO <= todayISOValue &&
        (isBoardWideViewport || selectedDateISO < todayISOValue);

    const showAddTaskButton = selectedDateISO >= todayISOValue;

    const userTimeZone =
        typeof Intl !== 'undefined'
            ? Intl.DateTimeFormat().resolvedOptions().timeZone || 'Australia/Sydney'
            : 'Australia/Sydney';

    const incompleteTasks = tasks.filter((t) => !t.completed);
    const completeTasks = tasks.filter((t) => t.completed);

    useEffect(() => {
        const token = session.token;
        if (!token) {
            setTasks([]);
            return;
        }

        let cancelled = false;
        const dateParam = utcIsoForLocalCalendarDate(selectedDateISO, userTimeZone);
        const currentParam = new Date().toISOString();

        const params = new URLSearchParams({
            date: dateParam,
            current_date: currentParam,
            timezone_name: userTimeZone,
            offset: '0',
            limit: '100',
        });

        setTasksLoading(true);
        setTasksError(null);

        fetch(`${backendURL}/tasks/self?${params.toString()}`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${token}`,
                Accept: 'application/json',
            },
        })
            .then(async (res) => {
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(text || res.statusText);
                }
                return res.json() as Promise<TaskPublicRow[]>;
            })
            .then((list) => {
                if (cancelled) return;
                setTasks(Array.isArray(list) ? list : []);
            })
            .catch(() => {
                if (cancelled) return;
                setTasksError('Could not load tasks.');
                setTasks([]);
            })
            .finally(() => {
                if (!cancelled) setTasksLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [session.token, selectedDateISO, userTimeZone]);

    const patchTaskCompleted = useCallback(
        async (taskId: number, completed: boolean) => {
            const token = session.token;
            if (!token) return false;
            const res = await fetch(`${backendURL}/task/${taskId}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify({completed}),
            });
            return res.ok;
        },
        [session.token],
    );

    const onToggleTask = (task: TaskPublicRow) => {
        const next = !task.completed;
        setTasks((prev) =>
            prev.map((t) => (t.id === task.id ? {...t, completed: next} : t)),
        );
        void patchTaskCompleted(task.id, next).then((ok) => {
            if (!ok) {
                setTasks((prev) =>
                    prev.map((t) => (t.id === task.id ? {...t, completed: task.completed} : t)),
                );
                setTasksError('Could not update task.');
            }
        });
    };

    let boardLayoutClass = 'tasks-panel-board--none';
    if (showTodoColumn && showDoneColumn) {
        boardLayoutClass = 'tasks-panel-board--both';
    } else if (showTodoColumn) {
        boardLayoutClass = 'tasks-panel-board--todo-only';
    } else if (showDoneColumn) {
        boardLayoutClass = 'tasks-panel-board--done-only';
    }

    const maxForContainer = useCallback(() => {
        const el = layoutContainerRef.current;
        const h = el?.getBoundingClientRect().height ?? window.innerHeight;
        return Math.max(MIN_EXPANDED_PX, h * MAX_VIEWPORT_RATIO);
    }, [layoutContainerRef]);

    const endDrag = useCallback(() => {
        setDragging(false);
        activePointerId.current = null;
    }, []);

    useEffect(() => {
        if (!dragging) return;
        const onPointerMove = (e: PointerEvent) => {
            if (e.pointerId !== activePointerId.current) return;
            const delta = dragStartY.current - e.clientY;
            const maxH = maxForContainer();
            const next = clamp(dragStartHeight.current + delta, COLLAPSED_PX, maxH);
            setHeightPx(next);
            if (next > COLLAPSED_PX + 2) {
                lastExpandedRef.current = next;
            }
        };
        const onPointerUp = (e: PointerEvent) => {
            if (e.pointerId !== activePointerId.current) return;
            endDrag();
            setHeightPx((h) => {
                if (h <= COLLAPSED_PX + 12) {
                    return COLLAPSED_PX;
                }
                if (h < MIN_EXPANDED_PX) {
                    return MIN_EXPANDED_PX;
                }
                lastExpandedRef.current = h;
                return h;
            });
        };
        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
        window.addEventListener('pointercancel', onPointerUp);
        return () => {
            window.removeEventListener('pointermove', onPointerMove);
            window.removeEventListener('pointerup', onPointerUp);
            window.removeEventListener('pointercancel', onPointerUp);
        };
    }, [dragging, endDrag, maxForContainer]);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const mq = window.matchMedia(BOARD_WIDE_BREAKPOINT_MQ);
        const onChange = () => setIsBoardWideViewport(mq.matches);
        onChange();
        mq.addEventListener('change', onChange);
        return () => mq.removeEventListener('change', onChange);
    }, []);

    const onResizeHandlePointerDown = (e: React.PointerEvent) => {
        e.preventDefault();
        if (e.button !== 0) return;
        dragStartY.current = e.clientY;
        dragStartHeight.current = heightPx;
        activePointerId.current = e.pointerId;
        setDragging(true);
    };

    const toggleOpen = () => {
        if (dragging) return;
        setHeightPx((h) => {
            if (h > COLLAPSED_PX + 1) {
                lastExpandedRef.current = h;
                return COLLAPSED_PX;
            }
            const target = lastExpandedRef.current;
            const maxH = maxForContainer();
            return clamp(target, MIN_EXPANDED_PX, maxH);
        });
    };

    function renderTaskRow(t: TaskPublicRow, column: 'todo' | 'done') {
        const safeBg = safeTaskBackgroundFromColourRaw(t.colour_raw);
        const bg =
            column === 'done' ? completedTaskBackgroundFromSafe(safeBg) : safeBg;
        const durLabel =
            isBoardWideViewport
                ? `${t.duration_mins} minute${t.duration_mins === 1 ? '' : 's'}`
                : `${t.duration_mins} min`;

        return (
            <div
                key={t.id}
                className={
                    'tasks-panel-task-row' +
                    (column === 'done' ? ' tasks-panel-task-row--done' : '')
                }
                style={{backgroundColor: bg}}
            >
                <button
                    type="button"
                    className="tasks-panel-task-check"
                    aria-label={t.completed ? 'Mark incomplete' : 'Mark complete'}
                    onClick={() => onToggleTask(t)}
                >
                    {t.completed ? <MdCheckBox aria-hidden /> : <MdCheckBoxOutlineBlank aria-hidden />}
                </button>
                <div className="tasks-panel-task-name-outer">
                    <span className="tasks-panel-task-name-inner">{t.name}</span>
                </div>
                <span className="tasks-panel-task-duration">{durLabel}</span>
            </div>
        );
    }

    return (
        <div
            className={'tasks-panel' + (dragging ? ' tasks-panel--dragging' : '')}
            style={{height: heightPx}}
            aria-expanded={open}
        >
            <div
                className="tasks-panel-resize-handle"
                onPointerDown={onResizeHandlePointerDown}
                role="separator"
                aria-orientation="horizontal"
                aria-label="Resize tasks panel"
            />
            <div className="tasks-panel-header">
                <button type="button" className="tasks-panel-header-toggle" onClick={toggleOpen}>
                    <p>
                        {open ? <MdKeyboardArrowDown /> : <MdKeyboardArrowUp />}
                        Tasks
                    </p>
                </button>
                <div
                    className={
                        'tasks-panel-date-selector' +
                        (open ? ' tasks-panel-date-selector--visible' : '')
                    }
                    aria-hidden={!open}
                >
                    <button
                        type="button"
                        className="tasks-panel-date-btn"
                        aria-label="Previous day"
                        onClick={(e) => {
                            e.stopPropagation();
                            setSelectedDateISO((iso) => {
                                const d = parseISODateLocal(iso);
                                d.setDate(d.getDate() - 1);
                                return formatISODateLocal(d);
                            });
                        }}
                    >
                        <MdArrowLeft aria-hidden />
                    </button>
                    <div className="tasks-panel-date-reset-slot">
                        {showResetDate ? (
                            <button
                                type="button"
                                className="tasks-panel-date-btn"
                                aria-label="Jump to today"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedDateISO(formatISODateLocal(new Date()));
                                }}
                            >
                                <MdRefresh aria-hidden />
                            </button>
                        ) : null}
                    </div>
                    <span className="tasks-panel-date-label">{dateLabel}</span>
                    <button
                        type="button"
                        className="tasks-panel-date-btn"
                        aria-label="Next day"
                        onClick={(e) => {
                            e.stopPropagation();
                            setSelectedDateISO((iso) => {
                                const d = parseISODateLocal(iso);
                                d.setDate(d.getDate() + 1);
                                return formatISODateLocal(d);
                            });
                        }}
                    >
                        <MdArrowRight aria-hidden />
                    </button>
                </div>
            </div>
            <div className="tasks-panel-body">
                {tasksError ? <p className="tasks-panel-tasks-error">{tasksError}</p> : null}
                {tasksLoading ? (
                    <p className="tasks-panel-placeholder">Loading tasks…</p>
                ) : null}
                <div className={'tasks-panel-board ' + boardLayoutClass}>
                    <div
                        className="tasks-panel-column tasks-panel-column--todo"
                        aria-hidden={!showTodoColumn}
                    >
                        <div
                            className={
                                'tasks-panel-column-card' +
                                (showTodoColumn && showDoneColumn
                                    ? ' tasks-panel-column-card--adjacent-left'
                                    : '')
                            }
                        >
                            <div className="tasks-panel-column-head">
                                <h3 className="tasks-panel-column-title">
                                    To-Do: {incompleteTasks.length}
                                </h3>
                            </div>
                            <div className="tasks-panel-column-body">
                                <div className="tasks-panel-column-scroll">
                                    {incompleteTasks.map((t) => renderTaskRow(t, 'todo'))}
                                </div>
                                {showAddTaskButton ? (
                                    <div className="tasks-panel-column-foot">
                                        <button type="button" className="tasks-panel-add-task">
                                            + Add Task
                                        </button>
                                    </div>
                                ) : null}
                            </div>
                        </div>
                    </div>
                    <div
                        className="tasks-panel-column tasks-panel-column--done"
                        aria-hidden={!showDoneColumn}
                    >
                        <div
                            className={
                                'tasks-panel-column-card' +
                                (showTodoColumn && showDoneColumn
                                    ? ' tasks-panel-column-card--adjacent-right'
                                    : '')
                            }
                        >
                            <div className="tasks-panel-column-head">
                                <h3 className="tasks-panel-column-title">
                                    Done: {completeTasks.length}
                                </h3>
                            </div>
                            <div className="tasks-panel-column-body">
                                <div className="tasks-panel-column-scroll">
                                    {completeTasks.map((t) => renderTaskRow(t, 'done'))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
