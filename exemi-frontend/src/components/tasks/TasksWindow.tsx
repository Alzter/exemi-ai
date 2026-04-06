import {useCallback, useEffect, useRef, useState, type RefObject} from 'react';
import {
    MdArrowLeft,
    MdArrowRight,
    MdCheckBox,
    MdCheckBoxOutlineBlank,
    MdClose,
    MdKeyboardArrowDown,
    MdKeyboardArrowUp,
    MdRefresh,
    MdAdd,
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
    /** Optimistic row while autofill/create is in flight */
    clientPending?: boolean;
};

type TaskCreateFromApi = {
    name: string;
    description: string;
    duration_mins: number;
    assignment_id: number | null;
    due_at: string;
};

function taskPublicJsonToRow(t: {
    id: number;
    name: string;
    duration_mins: number;
    completed: boolean;
    colour_raw?: string | null;
}): TaskPublicRow {
    return {
        id: t.id,
        name: t.name,
        duration_mins: t.duration_mins,
        completed: t.completed,
        colour_raw: t.colour_raw ?? null,
    };
}

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
    const [tasksError, setTasksError] = useState<string | null>(null);
    /** After LLM task generation (`/tasks_generate/self`); gates date picker and `/tasks/self`. */
    const [tasksBootstrapReady, setTasksBootstrapReady] = useState(() => !session.token);

    const [taskEntryOpen, setTaskEntryOpen] = useState(false);
    const [newTaskTitle, setNewTaskTitle] = useState('');
    const todoEntryContainerRef = useRef<HTMLDivElement>(null);
    const todoColumnScrollRef = useRef<HTMLDivElement>(null);
    const newTaskInputRef = useRef<HTMLInputElement>(null);
    const pendingTempIdRef = useRef(0);
    const prevSelectedDateISORef = useRef(selectedDateISO);

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

    const showAddTaskButton =
        selectedDateISO >= todayISOValue && Boolean(session.token && session.user?.username);

    const userTimeZone =
        typeof Intl !== 'undefined'
            ? Intl.DateTimeFormat().resolvedOptions().timeZone || 'Australia/Sydney'
            : 'Australia/Sydney';

    const incompleteTasks = tasks.filter((t) => !t.completed);
    const completeTasks = tasks.filter((t) => t.completed);

    useEffect(() => {
        if (!session.token) {
            setTasksBootstrapReady(true);
            return;
        }

        let cancelled = false;
        setTasksBootstrapReady(false);
        setTasksError(null);

        fetch(`${backendURL}/tasks_generate/self`, {
            method: 'GET',
            headers: {
                Authorization: `Bearer ${session.token}`,
                Accept: 'application/json',
            },
        })
            .then(async (res) => {
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(text || res.statusText);
                }
                await res.json();
            })
            .catch(() => {
                if (!cancelled) {
                    setTasksError('Could not generate or refresh tasks.');
                }
            })
            .finally(() => {
                if (!cancelled) setTasksBootstrapReady(true);
            });

        return () => {
            cancelled = true;
        };
    }, [session.token]);

    const reloadTasksFromApi = useCallback(async (): Promise<TaskPublicRow[] | null> => {
        const token = session.token;
        if (!token) return null;

        const dateParam = utcIsoForLocalCalendarDate(selectedDateISO, userTimeZone);
        const currentParam = new Date().toISOString();

        const params = new URLSearchParams({
            date: dateParam,
            current_date: currentParam,
            timezone_name: userTimeZone,
            offset: '0',
            limit: '100',
        });

        try {
            const res = await fetch(`${backendURL}/tasks/self?${params.toString()}`, {
                method: 'GET',
                headers: {
                    Authorization: `Bearer ${token}`,
                    Accept: 'application/json',
                },
            });
            if (!res.ok) return null;
            const list = (await res.json()) as TaskPublicRow[];
            return Array.isArray(list) ? list : [];
        } catch {
            return null;
        }
    }, [session.token, selectedDateISO, userTimeZone]);

    useEffect(() => {
        const token = session.token;
        if (!token) {
            setTasks([]);
            return;
        }

        if (!tasksBootstrapReady) {
            return;
        }

        let cancelled = false;
        setTasksError(null);

        void reloadTasksFromApi().then((list) => {
            if (cancelled) return;
            if (list === null) {
                setTasksError('Could not load tasks.');
                setTasks([]);
            } else {
                setTasks(list);
            }
        });

        return () => {
            cancelled = true;
        };
    }, [session.token, tasksBootstrapReady, reloadTasksFromApi]);

    const cancelTaskEntry = useCallback(() => {
        setTaskEntryOpen(false);
        setNewTaskTitle('');
    }, []);

    useEffect(() => {
        if (!taskEntryOpen) return;
        const id = requestAnimationFrame(() => {
            newTaskInputRef.current?.focus();
            newTaskInputRef.current?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
            const sc = todoColumnScrollRef.current;
            if (sc) {
                sc.scrollTo({top: sc.scrollHeight, behavior: 'smooth'});
            }
        });
        return () => cancelAnimationFrame(id);
    }, [taskEntryOpen]);

    useEffect(() => {
        if (!taskEntryOpen) return;
        const onPointerDown = (e: PointerEvent) => {
            const el = todoEntryContainerRef.current;
            if (!el) return;
            if (e.target instanceof Node && !el.contains(e.target)) {
                cancelTaskEntry();
            }
        };
        document.addEventListener('pointerdown', onPointerDown, true);
        return () => document.removeEventListener('pointerdown', onPointerDown, true);
    }, [taskEntryOpen, cancelTaskEntry]);

    useEffect(() => {
        if (prevSelectedDateISORef.current !== selectedDateISO) {
            prevSelectedDateISORef.current = selectedDateISO;
            cancelTaskEntry();
        }
    }, [selectedDateISO, cancelTaskEntry]);

    const confirmNewTask = useCallback(async () => {
        const name = newTaskTitle.trim();
        if (!name) return;
        const token = session.token;
        const username = session.user?.username;
        if (!token || !username) return;

        setTaskEntryOpen(false);
        setNewTaskTitle('');

        const tempId = --pendingTempIdRef.current;
        setTasks((prev) => [
            ...prev,
            {
                id: tempId,
                name,
                duration_mins: 0,
                completed: false,
                colour_raw: null,
                clientPending: true,
            },
        ]);

        const due_at = utcIsoForLocalCalendarDate(selectedDateISO, userTimeZone);

        const removePlaceholder = () => {
            setTasks((prev) => prev.filter((t) => t.id !== tempId));
        };

        try {
            const autofillRes = await fetch(
                `${backendURL}/task_autofill/${encodeURIComponent(username)}`,
                {
                    method: 'POST',
                    headers: {
                        Authorization: `Bearer ${token}`,
                        'Content-Type': 'application/json',
                        Accept: 'application/json',
                    },
                    body: JSON.stringify({name, due_at}),
                },
            );
            if (!autofillRes.ok) {
                removePlaceholder();
                setTasksError('Could not generate task details.');
                return;
            }

            const taskCreate = (await autofillRes.json()) as TaskCreateFromApi;

            const createRes = await fetch(`${backendURL}/task/${encodeURIComponent(username)}`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify(taskCreate),
            });

            if (!createRes.ok) {
                removePlaceholder();
                setTasksError('Could not save task.');
                return;
            }

            const createdJson = (await createRes.json()) as Parameters<typeof taskPublicJsonToRow>[0];
            const refreshed = await reloadTasksFromApi();
            if (refreshed !== null) {
                setTasks(refreshed);
                setTasksError(null);
            } else {
                setTasks((prev) => [
                    ...prev.filter((t) => t.id !== tempId),
                    taskPublicJsonToRow(createdJson),
                ]);
                setTasksError('Task saved; could not refresh the list.');
            }
        } catch {
            removePlaceholder();
            setTasksError('Could not add task.');
        }
    }, [
        newTaskTitle,
        session.token,
        session.user?.username,
        selectedDateISO,
        userTimeZone,
        reloadTasksFromApi,
    ]);

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
        const durLabel = t.clientPending
            ? '…'
            : isBoardWideViewport
              ? `${t.duration_mins} minute${t.duration_mins === 1 ? '' : 's'}`
              : `${t.duration_mins} min`;

        const isFutureDay = selectedDateISO > todayISOValue;
        const isPastDay = selectedDateISO < todayISOValue;
        const showCheckbox = !isFutureDay;
        const checkAriaLabel = isPastDay
            ? t.completed
                ? 'Completed'
                : 'Not completed'
            : t.completed
              ? 'Mark incomplete'
              : 'Mark complete';

        return (
            <div
                key={t.id}
                className={
                    'tasks-panel-task-row' +
                    (column === 'done' ? ' tasks-panel-task-row--done' : '')
                }
                style={{backgroundColor: bg}}
            >
                {showCheckbox ? (
                    <button
                        type="button"
                        className="tasks-panel-task-check"
                        aria-label={checkAriaLabel}
                        disabled={isPastDay || !!t.clientPending}
                        onClick={() => onToggleTask(t)}
                    >
                        {t.completed ? <MdCheckBox aria-hidden /> : <MdCheckBoxOutlineBlank aria-hidden />}
                    </button>
                ) : null}
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
            {/* <div
                className="tasks-panel-resize-handle"
                onPointerDown={onResizeHandlePointerDown}
                role="separator"
                aria-orientation="horizontal"
                aria-label="Resize tasks panel"
            /> */}

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
                        (open && tasksBootstrapReady ? ' tasks-panel-date-selector--visible' : '')
                    }
                    aria-hidden={!open || !tasksBootstrapReady}
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

            <div
                className="tasks-panel-resize-handle-large"
                onPointerDown={onResizeHandlePointerDown}
                role="separator"
                aria-orientation="horizontal"
                aria-label="Resize tasks panel"
            />

            <div
                className={
                    'tasks-panel-body' +
                    (session.token && !tasksBootstrapReady ? ' tasks-panel-body--bootstrap' : '')
                }
            >
                {tasksError ? <p className="tasks-panel-tasks-error">{tasksError}</p> : null}
                {session.token && !tasksBootstrapReady ? (
                    <div
                        className="tasks-panel-bootstrap-spinner"
                        role="status"
                        aria-live="polite"
                        aria-label="Generating and loading tasks"
                    >
                        <p>I am creating assignment tasks for you, please wait...</p>
                        <div className="loading-spinner" aria-hidden />
                    </div>
                ) : (
                    <div className={'tasks-panel-board ' + boardLayoutClass}>
                        <div
                            className={
                                'tasks-panel-column tasks-panel-column--todo' +
                                (showTodoColumn && showDoneColumn
                                    ? ' tasks-panel-column--adjacent-left'
                                    : '')
                            }
                            aria-hidden={!showTodoColumn}
                        >
                            <div ref={todoEntryContainerRef} className="tasks-panel-column-card">
                                <div className="tasks-panel-column-head">
                                    <h3 className="tasks-panel-column-title">
                                        To-Do: {incompleteTasks.length}
                                    </h3>
                                </div>
                                <div className="tasks-panel-column-body">
                                    <div ref={todoColumnScrollRef} className="tasks-panel-column-scroll">
                                        {incompleteTasks.map((t) => renderTaskRow(t, 'todo'))}
                                        {taskEntryOpen ? (
                                            <input
                                                ref={newTaskInputRef}
                                                type="text"
                                                className="tasks-panel-task-entry-input"
                                                value={newTaskTitle}
                                                onChange={(e) => setNewTaskTitle(e.target.value)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') {
                                                        e.preventDefault();
                                                        if (newTaskTitle.trim()) void confirmNewTask();
                                                    }
                                                    if (e.key === 'Escape') {
                                                        e.preventDefault();
                                                        cancelTaskEntry();
                                                    }
                                                }}
                                                placeholder="Task name"
                                                aria-label="New task name"
                                            />
                                        ) : null}
                                    </div>
                                    {showAddTaskButton ? (
                                        <div className="tasks-panel-column-foot">
                                            {taskEntryOpen ? (
                                                <div className="tasks-panel-task-entry-actions">
                                                    <button
                                                        type="button"
                                                        className="tasks-panel-task-entry-confirm"
                                                        disabled={!newTaskTitle.trim()}
                                                        onClick={() => void confirmNewTask()}
                                                        aria-label="Add task"
                                                    >
                                                        <MdAdd aria-hidden />
                                                        <span>Add</span>
                                                    </button>
                                                    <button
                                                        type="button"
                                                        className="tasks-panel-task-entry-cancel"
                                                        onClick={cancelTaskEntry}
                                                        aria-label="Cancel adding task"
                                                    >
                                                        <MdClose aria-hidden />
                                                    </button>
                                                </div>
                                            ) : (
                                                <button
                                                    type="button"
                                                    className="tasks-panel-add-task"
                                                    onClick={() => setTaskEntryOpen(true)}
                                                >
                                                    <MdAdd aria-hidden />
                                                    Add Task
                                                </button>
                                            )}
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        </div>
                        <div
                            className={
                                'tasks-panel-column tasks-panel-column--done' +
                                (showTodoColumn && showDoneColumn
                                    ? ' tasks-panel-column--adjacent-right'
                                    : '')
                            }
                            aria-hidden={!showDoneColumn}
                        >
                            <div className="tasks-panel-column-card">
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
                )}
            </div>
        </div>
    );
}
