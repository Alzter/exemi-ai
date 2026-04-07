import {
    useCallback,
    useEffect,
    useLayoutEffect,
    useMemo,
    useRef,
    useState,
    type RefObject,
} from 'react';
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
    MdPause,
    MdPlayArrow,
    MdCheck,
} from 'react-icons/md';
import {type Session} from '../../models';
import {
    completedTaskBackgroundFromSafe,
    safeTaskBackgroundFromColourRaw,
    saturatedProgressBarFromSafe,
    saturatedProgressBarBorderFromSafe,
    utcIsoForLocalCalendarDate,
} from '../../utils/taskBoardUtils';
import {call_task_deconstruction} from './taskDeconstruction';
import {
    clearActiveTaskTimer,
    readActiveTaskTimer,
    writeActiveTaskTimer,
} from './taskActiveTimerStorage';
import {TaskEditDialog, type TaskPublicRowPatch} from './TaskEditDialog';
import {TaskBreak} from './TaskBreak';
import {TaskBreakConfirm, type NextTaskPreview} from './TaskBreakConfirm';
import {TaskBreakSetup} from './TaskBreakSetup';
import {TaskForeground} from './TaskForeground';
import {TaskForegroundConfirm} from './TaskForegroundConfirm';
import type {TaskInboxItem} from './TaskInbox';

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
const FOREGROUND_BREAK_COUNTDOWN_THRESHOLD_SECS = 25 * 60;

const BOARD_WIDE_BREAKPOINT_MQ = '(min-width: 600px)';

function getDefaultExpandedHeightPx(): number {
    if (typeof window === 'undefined') return MIN_EXPANDED_PX;
    return window.innerHeight * DEFAULT_EXPANDED_VIEWPORT_RATIO;
}

function clamp(n: number, lo: number, hi: number) {
    return Math.min(hi, Math.max(lo, n));
}

function formatRemainingMmSs(totalSeconds: number): string {
    const s = Math.max(0, Math.floor(totalSeconds));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${String(r).padStart(2, '0')}`;
}

function computeForegroundBreakSegment(
    taskDurationMins: number,
    breakIntervalMins: number,
    effectiveProgressSeconds: number,
): {total: number; progress: number; remaining: number} {
    const durationSecs = Math.max(1, taskDurationMins * 60);
    const elapsed = Math.max(0, Math.floor(effectiveProgressSeconds));
    const remainingToFinish = Math.max(0, durationSecs - elapsed);
    const breakIntervalSecs = Math.max(60, breakIntervalMins * 60);
    const useSegmentCountdown =
        durationSecs > FOREGROUND_BREAK_COUNTDOWN_THRESHOLD_SECS &&
        breakIntervalSecs < durationSecs;
    if (!useSegmentCountdown) {
        return {
            total: durationSecs,
            progress: Math.min(durationSecs, elapsed),
            remaining: remainingToFinish,
        };
    }
    const segmentStart = Math.floor(elapsed / breakIntervalSecs) * breakIntervalSecs;
    const segmentEnd = Math.min(durationSecs, segmentStart + breakIntervalSecs);
    const segmentTotal = Math.max(1, segmentEnd - segmentStart);
    const segmentProgress = Math.max(
        0,
        Math.min(segmentTotal, elapsed - segmentStart),
    );
    return {
        total: segmentTotal,
        progress: segmentProgress,
        remaining: Math.max(0, segmentEnd - elapsed),
    };
}

type TaskPublicRow = {
    id: number;
    name: string;
    duration_mins: number;
    completed: boolean;
    /** Seconds worked; only surfaced in UI for incomplete tasks due today. */
    progress_secs: number;
    colour_raw: string | null;
    description?: string;
    assignment_id?: number | null;
    due_at?: string;
    break_interval_mins: number;
    /** Local calendar date (YYYY-MM-DD) this row was fetched or created for; checkbox past/future rules use this, not the picker */
    calendarDateISO?: string;
    /** Optimistic row while autofill/create is in flight */
    clientPending?: boolean;
    /** Local calendar date (YYYY-MM-DD) the pending task was created for; controls visibility when the date picker changes */
    clientPendingForDateISO?: string;
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
    progress_secs?: number;
    colour_raw?: string | null;
    description?: string;
    assignment_id?: number | null;
    due_at?: string;
    break_interval_mins: number;
}): TaskPublicRow {
    return {
        id: t.id,
        name: t.name,
        duration_mins: t.duration_mins,
        completed: t.completed,
        progress_secs: t.progress_secs ?? 0,
        colour_raw: t.colour_raw ?? null,
        description: t.description,
        assignment_id: t.assignment_id,
        due_at: t.due_at,
        break_interval_mins: t.break_interval_mins,
    };
}

function effectiveCalendarDateISO(t: TaskPublicRow, pickerDateISO: string): string {
    if (t.clientPending && t.clientPendingForDateISO) return t.clientPendingForDateISO;
    if (t.calendarDateISO) return t.calendarDateISO;
    return pickerDateISO;
}

function computeNextTodoPreview(
    taskRows: TaskPublicRow[],
    selectedDateISO: string,
    todayISOValue: string,
): NextTaskPreview | null {
    const incompleteTasks = taskRows.filter((t) => {
        if (t.completed) return false;
        if (t.clientPending && t.clientPendingForDateISO !== selectedDateISO) return false;
        return true;
    });
    const isDoing = (t: TaskPublicRow) =>
        !t.clientPending && selectedDateISO === todayISOValue && t.progress_secs > 0;
    const todoIncomplete = incompleteTasks.filter((t) => !isDoing(t));
    const first = todoIncomplete[0];
    if (!first) return null;
    return {
        id: first.id,
        name: first.name,
        duration_mins: first.duration_mins,
        colour_raw: first.colour_raw,
    };
}

type TasksWindowProps = {
    session: Session;
    layoutContainerRef: RefObject<HTMLDivElement | null>;
    /** False until Canvas curriculum sync has completed for this load (see LoggedInFlow `/canvas/all`). */
    canvasSyncReady: boolean;
};

export default function TasksWindow({session, layoutContainerRef, canvasSyncReady}: TasksWindowProps) {
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
    /** After Canvas sync + LLM task generation (`/tasks_generate/self`); gates date picker and `/tasks/self`. */
    const [tasksBootstrapReady, setTasksBootstrapReady] = useState(() => !session.token);

    const [taskEntryOpen, setTaskEntryOpen] = useState(false);
    const [newTaskTitle, setNewTaskTitle] = useState('');
    const todoEntryContainerRef = useRef<HTMLDivElement>(null);
    const todoColumnScrollRef = useRef<HTMLDivElement>(null);
    const newTaskInputRef = useRef<HTMLInputElement>(null);
    const pendingTempIdRef = useRef(0);
    const prevSelectedDateISORef = useRef(selectedDateISO);
    const doingExtraSecsRef = useRef<Record<number, number>>({});
    const doingTasksDisplayRef = useRef<TaskPublicRow[]>([]);
    const [doingTickCount, setDoingTick] = useState(0);

    const [doingCloseDialogOpen, setDoingCloseDialogOpen] = useState(false);
    const [playingDoingIds, setPlayingDoingIds] = useState<number[]>([]);
    const [todoEditTask, setTodoEditTask] = useState<TaskPublicRow | null>(null);

    const [focusConfirmTaskId, setFocusConfirmTaskId] = useState<number | null>(null);
    const [foregroundTaskId, setForegroundTaskId] = useState<number | null>(null);
    const [foregroundInboxItems, setForegroundInboxItems] = useState<TaskInboxItem[]>([]);
    const [breakConfirmOpen, setBreakConfirmOpen] = useState(false);
    const [breakSetupOpen, setBreakSetupOpen] = useState(false);
    const [breakRunOpen, setBreakRunOpen] = useState(false);
    const [breakDurationSecs, setBreakDurationSecs] = useState(15 * 60);
    const [breakFlowNextTask, setBreakFlowNextTask] = useState<NextTaskPreview | null>(null);
    const [breakCompletedCount, setBreakCompletedCount] = useState(1);
    const [breakResumeForegroundTaskId, setBreakResumeForegroundTaskId] = useState<number | null>(null);
    const prevFocusConfirmTaskIdRef = useRef<number | null>(null);
    const playingDoingIdsRef = useRef<number[]>([]);
    playingDoingIdsRef.current = playingDoingIds;
    const tasksRef = useRef<TaskPublicRow[]>([]);
    tasksRef.current = tasks;
    const foregroundTaskIdRef = useRef<number | null>(null);
    const selectedDateISORef = useRef(selectedDateISO);
    const tasksHydratedForDateRef = useRef<string | null>(null);
    const activeTimerRestoreAppliedRef = useRef(false);
    const allowActiveTimerDateRestoreRef = useRef(true);
    /** Last known row for the active playing task when it is not in `tasks` (e.g. date picker on another day). */
    const activeTimerTaskSnapshotRef = useRef<TaskPublicRow | null>(null);
    const didAutoExpandForActiveTimerRef = useRef(false);
    const appDocumentTitleRef = useRef('');
    const foregroundBreakTriggerInFlightRef = useRef(false);
    const previousForegroundProgressRef = useRef<{taskId: number; value: number} | null>(null);
    foregroundTaskIdRef.current = foregroundTaskId;
    selectedDateISORef.current = selectedDateISO;

    const dragStartY = useRef(0);
    const dragStartHeight = useRef(0);
    const activePointerId = useRef<number | null>(null);

    const open = heightPx > COLLAPSED_PX + 1;

    const todayISOValue = formatISODateLocal(new Date());
    const todayISORef = useRef(todayISOValue);
    todayISORef.current = todayISOValue;
    const dateLabel = formatTaskHeaderDateLabel(selectedDateISO, todayISOValue);
    const showResetDate = selectedDateISO !== todayISOValue;

    const showTodoColumn = selectedDateISO >= todayISOValue;
    /** Wide: show Done with To-Do for today. Narrow: show Done only for past days (To-Do hidden). */
    const showDoneColumn =
        selectedDateISO <= todayISOValue &&
        (isBoardWideViewport || selectedDateISO < todayISOValue);

    const showAddTaskButton =
        selectedDateISO >= todayISOValue && Boolean(session.token && session.user?.username);

    const pendingVisibleForSelectedDate = tasks.some(
        (t) => t.clientPending// && t.clientPendingForDateISO === selectedDateISO,
    );
    const addTaskBlockedByPending = pendingVisibleForSelectedDate;

    const userTimeZone =
        typeof Intl !== 'undefined'
            ? Intl.DateTimeFormat().resolvedOptions().timeZone || 'Australia/Sydney'
            : 'Australia/Sydney';

    const syncActiveTaskTimerPersist = useCallback(() => {
        const username = session.user?.username;
        const token = session.token;
        if (!username || !token) {
            clearActiveTaskTimer();
            return;
        }
        const playing = playingDoingIdsRef.current;
        if (playing.length !== 1) {
            return;
        }
        const id = playing[0]!;
        const live = tasksRef.current.find((t) => t.id === id && !t.clientPending);
        if (live) {
            activeTimerTaskSnapshotRef.current = {...live};
        }
        const row =
            live ??
            (activeTimerTaskSnapshotRef.current?.id === id
                ? activeTimerTaskSnapshotRef.current
                : null);
        if (!row || row.completed) {
            return;
        }
        const extra = doingExtraSecsRef.current[id] ?? 0;
        const effective = Math.max(0, Math.floor(row.progress_secs + extra));
        writeActiveTaskTimer({
            v: 1,
            username,
            taskId: id,
            progress_secs: effective,
            foreground: foregroundTaskIdRef.current === id,
            /** Doing / in-progress work is always anchored to "today" so restore loads the right task list after a date-picker change. */
            selectedDateISO: todayISORef.current,
        });
    }, [session.token, session.user?.username]);

    const incompleteTasks = tasks.filter((t) => {
        if (t.completed) return false;
        if (t.clientPending && t.clientPendingForDateISO !== selectedDateISO) return false;
        return true;
    });

    const isTaskInDoingColumn = (t: TaskPublicRow) =>
        !t.clientPending &&
        selectedDateISO === todayISOValue &&
        t.progress_secs > 0;

    const doingTasks = incompleteTasks.filter(isTaskInDoingColumn);
    const todoIncompleteTasks = incompleteTasks.filter((t) => !isTaskInDoingColumn(t));
    const showDoingCard = showTodoColumn && doingTasks.length > 0;

    const [doingAnimContent, setDoingAnimContent] = useState(showDoingCard);
    const [doingAnimExpanded, setDoingAnimExpanded] = useState(showDoingCard);

    const completeTasks = tasks.filter((t) => t.completed);

    useEffect(() => {
        if (showDoingCard && doingTasks.length > 0) {
            doingTasksDisplayRef.current = doingTasks;
        }
    }, [showDoingCard, doingTasks]);

    useEffect(() => {
        if (showDoingCard) {
            setDoingAnimContent(true);
            const id = requestAnimationFrame(() => {
                requestAnimationFrame(() => setDoingAnimExpanded(true));
            });
            return () => cancelAnimationFrame(id);
        }
        setDoingAnimExpanded(false);
    }, [showDoingCard]);

    const onDoingSlotTransitionEnd = useCallback(
        (e: React.TransitionEvent<HTMLDivElement>) => {
            if (e.target !== e.currentTarget) return;
            if (e.propertyName !== 'grid-template-rows') return;
            if (!showDoingCard) setDoingAnimContent(false);
        },
        [showDoingCard],
    );

    /** Stable key so effects do not run every render (doingTasks is a new [] each time). */
    const doingTaskIdsKey = useMemo(() => {
        const ids: number[] = [];
        for (const t of tasks) {
            if (t.completed) continue;
            if (t.clientPending && t.clientPendingForDateISO !== selectedDateISO) continue;
            if (
                !t.clientPending &&
                selectedDateISO === todayISOValue &&
                t.progress_secs > 0
            ) {
                ids.push(t.id);
            }
        }
        ids.sort((a, b) => a - b);
        return ids.join(',');
    }, [tasks, selectedDateISO, todayISOValue]);

    useEffect(() => {
        if (doingTaskIdsKey === '') {
            setDoingCloseDialogOpen(false);
            if (playingDoingIdsRef.current.length === 1) {
                return;
            }
            setPlayingDoingIds([]);
            doingExtraSecsRef.current = {};
            return;
        }
        const idSet = new Set<number>();
        for (const part of doingTaskIdsKey.split(',')) {
            const n = Number(part);
            if (Number.isFinite(n)) idSet.add(n);
        }
        const activePlaying = playingDoingIdsRef.current[0];
        if (activePlaying !== undefined) {
            idSet.add(activePlaying);
        }
        setPlayingDoingIds((prev) => {
            const next = prev.filter((id) => idSet.has(id));
            const normalized = next.length <= 1 ? next : [next[0]!];
            if (
                normalized.length === prev.length &&
                normalized.every((id, i) => id === prev[i])
            ) {
                return prev;
            }
            return normalized;
        });
        const ref = doingExtraSecsRef.current;
        for (const k of Object.keys(ref)) {
            const n = Number(k);
            if (!idSet.has(n) && n !== activePlaying) delete ref[n];
        }
    }, [doingTaskIdsKey]);

    useEffect(() => {
        if (!session.token) {
            setTasksBootstrapReady(true);
            return;
        }

        if (!canvasSyncReady) {
            setTasksBootstrapReady(false);
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
    }, [session.token, canvasSyncReady]);

    const reloadTasksFromApi = useCallback(
        async (forLocalDateISO: string): Promise<TaskPublicRow[] | null> => {
            const token = session.token;
            if (!token) return null;

            const dateParam = utcIsoForLocalCalendarDate(forLocalDateISO, userTimeZone);
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
                const raw = (await res.json()) as TaskPublicRow[];
                const list = Array.isArray(raw) ? raw : [];
                return list.map((row) => ({
                    ...taskPublicJsonToRow(row),
                    calendarDateISO: forLocalDateISO,
                }));
            } catch {
                return null;
            }
        },
        [session.token, userTimeZone],
    );

    useEffect(() => {
        const token = session.token;
        if (!token) {
            setTasks([]);
            clearActiveTaskTimer();
            tasksHydratedForDateRef.current = null;
            activeTimerRestoreAppliedRef.current = false;
            allowActiveTimerDateRestoreRef.current = true;
            didAutoExpandForActiveTimerRef.current = false;
            return;
        }

        if (!tasksBootstrapReady) {
            return;
        }

        let cancelled = false;
        setTasksError(null);

        const requestedDate = selectedDateISO;
        tasksHydratedForDateRef.current = null;
        void reloadTasksFromApi(requestedDate).then((list) => {
            if (cancelled) return;
            tasksHydratedForDateRef.current = requestedDate;
            if (list === null) {
                setTasksError('Could not load tasks.');
                setTasks((prev) => prev.filter((t) => t.clientPending));
            } else {
                setTasks((prev) => {
                    const pendingAll = prev.filter((t) => t.clientPending);
                    return [...list, ...pendingAll];
                });
            }
        });

        return () => {
            cancelled = true;
        };
    }, [session.token, tasksBootstrapReady, selectedDateISO, reloadTasksFromApi]);

    useEffect(() => {
        const token = session.token;
        const username = session.user?.username;
        if (!token || !username || !tasksBootstrapReady) return;
        if (tasksHydratedForDateRef.current !== selectedDateISO) return;
        if (activeTimerRestoreAppliedRef.current) return;

        const raw = readActiveTaskTimer();
        if (!raw || raw.username !== username) {
            if (raw && raw.username !== username) {
                clearActiveTaskTimer();
            }
            allowActiveTimerDateRestoreRef.current = false;
            activeTimerRestoreAppliedRef.current = true;
            return;
        }

        if (raw.selectedDateISO !== selectedDateISO) {
            if (allowActiveTimerDateRestoreRef.current) {
                setSelectedDateISO(raw.selectedDateISO);
                return;
            }
            activeTimerRestoreAppliedRef.current = true;
            return;
        }

        allowActiveTimerDateRestoreRef.current = false;

        const row = tasks.find((t) => t.id === raw.taskId && !t.completed);
        if (!row) {
            clearActiveTaskTimer();
            activeTimerRestoreAppliedRef.current = true;
            return;
        }

        activeTimerRestoreAppliedRef.current = true;
        doingExtraSecsRef.current = {};
        doingExtraSecsRef.current[raw.taskId] = 0;
        setTasks((prev) =>
            prev.map((t) =>
                t.id === raw.taskId ? {...t, progress_secs: raw.progress_secs} : t,
            ),
        );
        setPlayingDoingIds([raw.taskId]);
        activeTimerTaskSnapshotRef.current = {...row, progress_secs: raw.progress_secs};
        if (raw.foreground) {
            setForegroundTaskId(raw.taskId);
        }
    }, [
        session.token,
        session.user?.username,
        tasksBootstrapReady,
        selectedDateISO,
        tasks,
    ]);

    useEffect(() => {
        queueMicrotask(() => {
            syncActiveTaskTimerPersist();
        });
    }, [playingDoingIds, foregroundTaskId, selectedDateISO, syncActiveTaskTimerPersist]);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const persist = () => {
            syncActiveTaskTimerPersist();
        };
        const onVis = () => {
            if (document.visibilityState === 'hidden') {
                syncActiveTaskTimerPersist();
            }
        };
        window.addEventListener('beforeunload', persist);
        document.addEventListener('visibilitychange', onVis);
        return () => {
            window.removeEventListener('beforeunload', persist);
            document.removeEventListener('visibilitychange', onVis);
        };
    }, [syncActiveTaskTimerPersist]);

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

        const taskDateISO = selectedDateISO;

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
                progress_secs: 0,
                colour_raw: null,
                clientPending: true,
                clientPendingForDateISO: taskDateISO,
                break_interval_mins: session.user?.task_break_interval_mins || 25,
            },
        ]);

        const due_at = utcIsoForLocalCalendarDate(taskDateISO, userTimeZone);

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
            const refreshed = await reloadTasksFromApi(taskDateISO);
            if (refreshed !== null) {
                setTasks(refreshed);
                setTasksError(null);
            } else {
                setTasks((prev) => [
                    ...prev.filter((t) => t.id !== tempId),
                    {...taskPublicJsonToRow(createdJson), calendarDateISO: taskDateISO},
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
            const body =
                completed ? {completed: true, progress_secs: 0} : {completed: false};
            const res = await fetch(`${backendURL}/task/${taskId}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify(body),
            });
            return res.ok;
        },
        [session.token],
    );

    const patchTaskProgressSecs = useCallback(
        async (taskId: number, progress_secs: number) => {
            const token = session.token;
            if (!token) return false;
            const res = await fetch(`${backendURL}/task/${taskId}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify({progress_secs}),
            });
            return res.ok;
        },
        [session.token],
    );

    useEffect(() => {
        if (playingDoingIds.length === 0) return;
        const t = window.setInterval(() => {
            const ids = [...playingDoingIdsRef.current];
            for (const id of ids) {
                const live = tasksRef.current.find(
                    (row) => row.id === id && !row.clientPending,
                );
                if (live) {
                    activeTimerTaskSnapshotRef.current = {...live};
                }
                const task =
                    live ??
                    (activeTimerTaskSnapshotRef.current?.id === id
                        ? activeTimerTaskSnapshotRef.current
                        : null);
                if (!task || task.clientPending) continue;

                doingExtraSecsRef.current[id] = (doingExtraSecsRef.current[id] ?? 0) + 1;
                const totalSecs = Math.max(task.duration_mins * 60, 1);
                const effective =
                    task.progress_secs + (doingExtraSecsRef.current[id] ?? 0);

                if (effective >= totalSecs) {
                    doingExtraSecsRef.current[id] = 0;
                    setTasks((prev) => {
                        if (!prev.some((row) => row.id === id)) return prev;
                        return prev.map((row) =>
                            row.id === id ? {...row, progress_secs: totalSecs} : row,
                        );
                    });
                    const snap = activeTimerTaskSnapshotRef.current;
                    if (snap && snap.id === id) {
                        activeTimerTaskSnapshotRef.current = {
                            ...snap,
                            progress_secs: totalSecs,
                        };
                    }
                    void patchTaskProgressSecs(id, totalSecs).then((ok) => {
                        if (!ok) setTasksError('Could not save progress.');
                    });
                    setPlayingDoingIds((prev) => prev.filter((x) => x !== id));
                    clearActiveTaskTimer();
                }
            }
            setDoingTick((x) => x + 1);
            syncActiveTaskTimerPersist();
        }, 1000);
        return () => window.clearInterval(t);
    }, [playingDoingIds, patchTaskProgressSecs, syncActiveTaskTimerPersist]);

    useEffect(() => {
        if (playingDoingIds.length === 0) {
            activeTimerTaskSnapshotRef.current = null;
        }
    }, [playingDoingIds]);

    const patchTaskFields = useCallback(
        async (taskId: number, body: Record<string, unknown>) => {
            const token = session.token;
            if (!token) return false;
            const res = await fetch(`${backendURL}/task/${taskId}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify(body),
            });
            return res.ok;
        },
        [session.token],
    );

    const flushDoingProgress = useCallback(
        async (taskId: number) => {
            const extra = doingExtraSecsRef.current[taskId] ?? 0;
            if (extra <= 0) return;
            doingExtraSecsRef.current[taskId] = 0;
            let merged: number | null = null;
            setTasks((prev) => {
                const task = prev.find((t) => t.id === taskId);
                if (task) {
                    merged = task.progress_secs + extra;
                    return prev.map((t) => (t.id === taskId ? {...t, progress_secs: merged!} : t));
                }
                const snap = activeTimerTaskSnapshotRef.current;
                if (snap && snap.id === taskId) {
                    merged = snap.progress_secs + extra;
                    activeTimerTaskSnapshotRef.current = {
                        ...snap,
                        progress_secs: merged,
                    };
                }
                return prev;
            });
            if (merged !== null) {
                const ok = await patchTaskProgressSecs(taskId, merged);
                if (!ok) setTasksError('Could not save progress.');
            }
        },
        [patchTaskProgressSecs],
    );

    const handleTaskMerged = useCallback((patch: TaskPublicRowPatch) => {
        setTasks((prev) => prev.map((t) => (t.id === patch.id ? {...t, ...patch} : t)));
        setTodoEditTask((prev) => (prev && prev.id === patch.id ? {...prev, ...patch} : prev));
    }, []);

    const handleTaskRemoved = useCallback((id: number) => {
        setTasks((prev) => prev.filter((t) => t.id !== id));
        setTodoEditTask((prev) => (prev && prev.id === id ? null : prev));
    }, []);

    const handleEditBoardReload = useCallback(() => {
        void reloadTasksFromApi(selectedDateISO).then((list) => {
            if (list === null) return;
            setTasks((prev) => {
                const pending = prev.filter((t) => t.clientPending);
                return [...list, ...pending];
            });
        });
    }, [reloadTasksFromApi, selectedDateISO]);

    const openFocusConfirmForTask = useCallback((taskId: number) => {
        if (prevFocusConfirmTaskIdRef.current !== taskId) {
            setForegroundInboxItems([]);
        }
        prevFocusConfirmTaskIdRef.current = taskId;
        setFocusConfirmTaskId(taskId);
    }, []);

    const handleStartWorkFromEdit = useCallback(
        (taskId: number) => {
            openFocusConfirmForTask(taskId);
        },
        [openFocusConfirmForTask],
    );

    const onToggleTask = (task: TaskPublicRow) => {
        const next = !task.completed;
        if (next) {
            const ls = readActiveTaskTimer();
            if (ls?.taskId === task.id) {
                clearActiveTaskTimer();
            }
            delete doingExtraSecsRef.current[task.id];
            setPlayingDoingIds((prev) => prev.filter((id) => id !== task.id));
        }
        setTasks((prev) =>
            prev.map((t) =>
                t.id === task.id
                    ? {...t, completed: next, progress_secs: next ? 0 : t.progress_secs}
                    : t,
            ),
        );
        void patchTaskCompleted(task.id, next).then((ok) => {
            if (!ok) {
                setTasks((prev) =>
                    prev.map((t) =>
                        t.id === task.id
                            ? {...t, completed: task.completed, progress_secs: task.progress_secs}
                            : t,
                    ),
                );
                setTasksError('Could not update task.');
            }
        });
    };

    const toggleDoingPlayPause = useCallback(
        async (taskId: number) => {
            const currently = playingDoingIdsRef.current;
            if (currently.includes(taskId)) {
                await flushDoingProgress(taskId);
                clearActiveTaskTimer();
                setPlayingDoingIds((prev) => prev.filter((id) => id !== taskId));
                return;
            }
            const others = currently.filter((id) => id !== taskId);
            for (const id of others) {
                await flushDoingProgress(id);
            }
            setPlayingDoingIds([taskId]);
            const row = tasksRef.current.find((t) => t.id === taskId && !t.clientPending);
            if (row) activeTimerTaskSnapshotRef.current = {...row};
        },
        [flushDoingProgress],
    );

    useEffect(() => {
        if (focusConfirmTaskId !== null && !tasks.some((t) => t.id === focusConfirmTaskId)) {
            setFocusConfirmTaskId(null);
        }
    }, [focusConfirmTaskId, tasks]);

    useEffect(() => {
        if (foregroundTaskId === null) return;
        if (tasks.some((t) => t.id === foregroundTaskId)) return;
        if (activeTimerTaskSnapshotRef.current?.id === foregroundTaskId) return;
        setForegroundTaskId(null);
    }, [foregroundTaskId, tasks]);

    const focusConfirmRow =
        focusConfirmTaskId !== null ? tasks.find((t) => t.id === focusConfirmTaskId) : undefined;

    const onFocusConfirmClose = useCallback(() => {
        setFocusConfirmTaskId(null);
    }, []);

    const onFocusConfirmBackground = useCallback(async () => {
        if (focusConfirmTaskId === null) return;
        const tid = focusConfirmTaskId;
        const others = playingDoingIdsRef.current.filter((id) => id !== tid);
        for (const id of others) {
            await flushDoingProgress(id);
        }
        setPlayingDoingIds([tid]);
        const bgRow = tasksRef.current.find((t) => t.id === tid && !t.clientPending);
        if (bgRow) activeTimerTaskSnapshotRef.current = {...bgRow};
        setFocusConfirmTaskId(null);
    }, [focusConfirmTaskId, flushDoingProgress]);

    const startForegroundTask = useCallback(
        async (tid: number) => {
        const others = playingDoingIdsRef.current.filter((id) => id !== tid);
        for (const id of others) {
            await flushDoingProgress(id);
        }
        setPlayingDoingIds([tid]);
        const fgRow = tasksRef.current.find((t) => t.id === tid && !t.clientPending);
        if (fgRow) activeTimerTaskSnapshotRef.current = {...fgRow};
        setForegroundTaskId(tid);
    },
    [flushDoingProgress]);

    const onFocusConfirmForeground = useCallback(async () => {
        if (focusConfirmTaskId === null) return;
        await startForegroundTask(focusConfirmTaskId);
        setFocusConfirmTaskId(null);
    }, [focusConfirmTaskId, startForegroundTask]);

    const onForegroundPauseToBackground = useCallback(async () => {
        if (foregroundTaskId === null) return;
        const tid = foregroundTaskId;
        await flushDoingProgress(tid);
        clearActiveTaskTimer();
        setPlayingDoingIds((prev) => prev.filter((id) => id !== tid));
        setForegroundTaskId(null);
    }, [foregroundTaskId, flushDoingProgress]);

    const onForegroundNeedHelp = useCallback(async () => {
        if (foregroundTaskId === null) return;
        const tid = foregroundTaskId;
        await flushDoingProgress(tid);
        clearActiveTaskTimer();
        call_task_deconstruction(tid);
        setPlayingDoingIds((prev) => prev.filter((id) => id !== tid));
        setForegroundTaskId(null);
    }, [foregroundTaskId, flushDoingProgress]);

    const startForegroundBreakFlow = useCallback(async () => {
        if (foregroundTaskIdRef.current === null) return;
        if (foregroundBreakTriggerInFlightRef.current) return;
        foregroundBreakTriggerInFlightRef.current = true;
        const tid = foregroundTaskIdRef.current;
        try {
            await flushDoingProgress(tid);
            clearActiveTaskTimer();
            setPlayingDoingIds((prev) => prev.filter((id) => id !== tid));
            setForegroundTaskId(null);
            setBreakConfirmOpen(false);
            setBreakResumeForegroundTaskId(tid);
            setBreakSetupOpen(true);
        } finally {
            foregroundBreakTriggerInFlightRef.current = false;
        }
    }, [flushDoingProgress]);

    const onForegroundFinished = useCallback(async () => {
        if (foregroundTaskId === null || !session.token) return;
        const tid = foregroundTaskId;
        const row = tasks.find((t) => t.id === tid);
        if (!row) return;
        doingExtraSecsRef.current[tid] = 0;

        const ok = await patchTaskFields(tid, {progress_secs: 0, completed: true});
        if (!ok) {
            setTasksError('Could not complete task.');
            return;
        }
        clearActiveTaskTimer();

        const dueForInbox = utcIsoForLocalCalendarDate(selectedDateISO, userTimeZone);
        for (const item of foregroundInboxItems) {
            const res = await fetch(`${backendURL}/task`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${session.token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify({
                    name: item.name,
                    description: '',
                    duration_mins: 15,
                    assignment_id: null,
                    due_at: dueForInbox,
                }),
            });
            if (!res.ok) setTasksError('Could not save an inbox task.');
        }

        const hyp = tasks.map((t) =>
            t.id === tid ? {...t, completed: true, progress_secs: 0} : t,
        );
        const nextPreview = computeNextTodoPreview(hyp, selectedDateISO, todayISOValue);

        setTasks((prev) =>
            prev.map((t) => (t.id === tid ? {...t, completed: true, progress_secs: 0} : t)),
        );
        setPlayingDoingIds((prev) => prev.filter((id) => id !== tid));
        setForegroundTaskId(null);
        setBreakResumeForegroundTaskId(null);
        setForegroundInboxItems([]);
        setBreakFlowNextTask(nextPreview);
        setBreakCompletedCount(1);
        setBreakConfirmOpen(true);

        void reloadTasksFromApi(selectedDateISO).then((list) => {
            if (list === null) return;
            setTasks((prev) => {
                const pending = prev.filter((t) => t.clientPending);
                return [...list, ...pending];
            });
        });
    }, [
        foregroundTaskId,
        session.token,
        tasks,
        foregroundInboxItems,
        patchTaskFields,
        selectedDateISO,
        todayISOValue,
        userTimeZone,
        reloadTasksFromApi,
    ]);

    const onBreakConfirmClose = useCallback(() => setBreakConfirmOpen(false), []);

    const onBreakTakeBreak = useCallback(() => {
        setBreakConfirmOpen(false);
        setBreakSetupOpen(true);
    }, []);

    const onBreakKeepGoing = useCallback(() => {
        setBreakConfirmOpen(false);
        const next = breakFlowNextTask;
        if (next) {
            void startForegroundTask(next.id);
        }
    }, [breakFlowNextTask, startForegroundTask]);

    const onBreakSetupClose = useCallback(() => {
        setBreakSetupOpen(false);
        if (breakResumeForegroundTaskId !== null) {
            const tid = breakResumeForegroundTaskId;
            setBreakResumeForegroundTaskId(null);
            void startForegroundTask(tid);
        }
    }, [breakResumeForegroundTaskId, startForegroundTask]);

    const onBreakSetupConfirm = useCallback((mins: number) => {
        setBreakSetupOpen(false);
        setBreakDurationSecs(mins * 60);
        setBreakRunOpen(true);
    }, []);

    const onBreakRunClose = useCallback(() => {
        setBreakRunOpen(false);
        if (breakResumeForegroundTaskId !== null) {
            const tid = breakResumeForegroundTaskId;
            setBreakResumeForegroundTaskId(null);
            void startForegroundTask(tid);
        }
    }, [breakResumeForegroundTaskId, startForegroundTask]);

    const onBreakNextTask = useCallback(() => {
        setBreakRunOpen(false);
        if (breakResumeForegroundTaskId !== null) {
            const tid = breakResumeForegroundTaskId;
            setBreakResumeForegroundTaskId(null);
            void startForegroundTask(tid);
        }
    }, [breakResumeForegroundTaskId, startForegroundTask]);

    const onDoingDialogYes = useCallback(() => {
        const first = doingTasks[0];
        if (first) call_task_deconstruction(first.id);
        setDoingCloseDialogOpen(false);
    }, [doingTasks]);

    const onDoingDialogNo = useCallback(() => {
        const ids = doingTasks.map((t) => t.id);
        if (ids.length === 0) {
            setDoingCloseDialogOpen(false);
            return;
        }
        setDoingCloseDialogOpen(false);
        clearActiveTaskTimer();
        setPlayingDoingIds([]);
        for (const id of ids) {
            delete doingExtraSecsRef.current[id];
        }
        setTasks((prev) =>
            prev.map((t) => (ids.includes(t.id) ? {...t, progress_secs: 0} : t)),
        );
        void Promise.all(ids.map((id) => patchTaskProgressSecs(id, 0))).then((results) => {
            if (results.some((ok) => !ok)) {
                setTasksError('Could not reset task progress.');
                void reloadTasksFromApi(selectedDateISO).then((list) => {
                    if (list !== null) setTasks(list);
                });
            }
        });
    }, [doingTasks, patchTaskProgressSecs, reloadTasksFromApi, selectedDateISO]);

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

    useEffect(() => {
        if (!tasksBootstrapReady || !session.token || !session.user?.username) return;
        if (didAutoExpandForActiveTimerRef.current) return;
        const u = session.user.username;
        const persisted = readActiveTaskTimer();
        const persistedMine = persisted && persisted.username === u;
        const playingBackground =
            playingDoingIds.length === 1 && foregroundTaskId === null;
        const foregroundOpen = foregroundTaskId !== null;
        if (!persistedMine && !playingBackground && !foregroundOpen) return;
        didAutoExpandForActiveTimerRef.current = true;
        setHeightPx((h) => {
            if (h > COLLAPSED_PX + 1) return h;
            return clamp(lastExpandedRef.current, MIN_EXPANDED_PX, maxForContainer());
        });
    }, [
        tasksBootstrapReady,
        session.token,
        session.user?.username,
        playingDoingIds,
        foregroundTaskId,
        maxForContainer,
    ]);

    useLayoutEffect(() => {
        if (typeof document === 'undefined') return;
        appDocumentTitleRef.current = document.title;
    }, []);

    useEffect(() => {
        if (typeof document === 'undefined') return;
        if (playingDoingIds.length !== 1) {
            document.title = appDocumentTitleRef.current;
            return;
        }
        const id = playingDoingIds[0]!;
        const live = tasks.find((t) => t.id === id && !t.clientPending);
        const row =
            live ??
            (activeTimerTaskSnapshotRef.current?.id === id
                ? activeTimerTaskSnapshotRef.current
                : null);
        if (!row || row.completed) {
            document.title = appDocumentTitleRef.current;
            return;
        }
        const extra = doingExtraSecsRef.current[id] ?? 0;
        const effectiveProgress = row.progress_secs + extra;
        const remainingSecs =
            foregroundTaskIdRef.current === id
                ? computeForegroundBreakSegment(
                      row.duration_mins,
                      row.break_interval_mins,
                      effectiveProgress,
                  ).remaining
                : Math.max(0, Math.max(row.duration_mins * 60, 1) - effectiveProgress);
        document.title = `${formatRemainingMmSs(remainingSecs)} - ${row.name}`;
    }, [doingTickCount, playingDoingIds, tasks]);

    useEffect(() => {
        return () => {
            if (typeof document === 'undefined') return;
            document.title = appDocumentTitleRef.current;
        };
    }, []);

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

        const rowDateISO = effectiveCalendarDateISO(t, selectedDateISO);
        const isFutureDay = rowDateISO > todayISOValue;
        const isPastDay = rowDateISO < todayISOValue;
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
                    (column === 'done' ? ' tasks-panel-task-row--done' : '') +
                    (t.clientPending ? ' tasks-panel-task-row--pending' : '') +
                    (column === 'todo' && !t.clientPending
                        ? ' tasks-panel-task-row--todo-editable'
                        : '')
                }
                style={{backgroundColor: bg}}
                onClick={
                    column === 'todo' && !t.clientPending
                        ? () => {
                              setTodoEditTask(t);
                          }
                        : undefined
                }
            >
                {showCheckbox ? (
                    <button
                        type="button"
                        className="checkbox"
                        aria-label={checkAriaLabel}
                        disabled={isPastDay || !!t.clientPending}
                        onClick={(ev) => {
                            ev.stopPropagation();
                            onToggleTask(t);
                        }}
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

    function formatMmSs(totalSeconds: number): string {
        return formatRemainingMmSs(totalSeconds);
    }

    function renderDoingTaskRow(t: TaskPublicRow) {
        void doingTickCount;
        const safeBg = safeTaskBackgroundFromColourRaw(t.colour_raw);
        const barColor = saturatedProgressBarFromSafe(safeBg);
        const barBorderColor = saturatedProgressBarBorderFromSafe(safeBg);
        const extra = doingExtraSecsRef.current[t.id] ?? 0;
        const effectiveProgress = t.progress_secs + extra;
        const totalSecs = Math.max(t.duration_mins * 60, 1);
        const progressPct = Math.min(100, (effectiveProgress / totalSecs) * 100);
        const remainingSecs = Math.max(0, totalSecs - effectiveProgress);
        const timeLabel = formatMmSs(remainingSecs);
        const playing = playingDoingIds.includes(t.id);
        const atDurationCap = effectiveProgress >= totalSecs;

        return (
            <div
                key={t.id}
                className="tasks-panel-task-row tasks-panel-task-row--doing"
                style={{backgroundColor: safeBg, borderColor: barBorderColor}}
            >
                <div
                    className="tasks-panel-doing-progress-fill"
                    style={{width: `calc(${progressPct}% - ${46 * progressPct / 100}px)`, backgroundColor: barColor, borderRadius: progressPct === 100 ? 0 : "4px"}}
                    aria-hidden
                />
                <div className="tasks-panel-doing-row-content">
                    <button
                        type="button"
                        className="checkbox"
                        aria-label={t.completed ? 'Mark incomplete' : 'Mark complete'}
                        onClick={() => onToggleTask(t)}
                    >
                        {t.completed ? <MdCheckBox aria-hidden /> : <MdCheckBoxOutlineBlank aria-hidden />}
                    </button>
                    <div className="tasks-panel-task-name-outer">
                        <span className="tasks-panel-task-name-inner">{t.name}</span>
                    </div>
                    <span
                        className="tasks-panel-task-duration tasks-panel-doing-timer"
                        style={{fontWeight: playing ? 800 : 500, fontSize: playing ? "1.25em" : "1em", opacity: playing ? 1 : 0.85}}
                    >{timeLabel}</span>
                    <button
                        type="button"
                        className="tasks-panel-doing-play-toggle"
                        aria-label={
                            atDurationCap
                                ? 'Scheduled time is complete'
                                : playing
                                  ? 'Pause timer'
                                  : 'Resume timer'
                        }
                        disabled={atDurationCap}
                        style={{borderColor: atDurationCap ? "transparent" : barBorderColor, backgroundColor: atDurationCap ? barColor : "transparent"}}
                        onClick={() => {
                            void toggleDoingPlayPause(t.id);
                        }}
                    >
                        {atDurationCap ? <MdCheck aria-hidden /> : playing ? <MdPause aria-hidden /> : <MdPlayArrow aria-hidden />}
                    </button>
                </div>
            </div>
        );
    }

    const doingTasksForUi =
        showDoingCard ? doingTasks : doingAnimContent ? doingTasksDisplayRef.current : [];

    const activeBackgroundDoingId = playingDoingIds[0];
    const activeBackgroundDoingTask =
        activeBackgroundDoingId !== undefined
            ? doingTasksForUi.find((row) => row.id === activeBackgroundDoingId) ??
              (activeTimerTaskSnapshotRef.current?.id === activeBackgroundDoingId
                  ? activeTimerTaskSnapshotRef.current
                  : undefined)
            : undefined;
    const doingCardBackground =
        activeBackgroundDoingTask !== undefined
            ? safeTaskBackgroundFromColourRaw(activeBackgroundDoingTask.colour_raw)
            : '#eee';

    void doingTickCount;
    let foregroundTaskRow =
        foregroundTaskId !== null ? tasks.find((t) => t.id === foregroundTaskId) : undefined;
    if (!foregroundTaskRow && foregroundTaskId !== null) {
        const snap = activeTimerTaskSnapshotRef.current;
        if (snap?.id === foregroundTaskId) foregroundTaskRow = snap;
    }
    const foregroundProgressEffective =
        foregroundTaskRow && foregroundTaskId !== null
            ? foregroundTaskRow.progress_secs + (doingExtraSecsRef.current[foregroundTaskId] ?? 0)
            : 0;
    const foregroundBreakSegment =
        foregroundTaskRow && foregroundTaskId !== null
            ? computeForegroundBreakSegment(
                  foregroundTaskRow.duration_mins,
                  foregroundTaskRow.break_interval_mins,
                  foregroundProgressEffective,
              )
            : {total: 1, progress: 0, remaining: 0};

    useEffect(() => {
        if (foregroundTaskId === null || !foregroundTaskRow) {
            previousForegroundProgressRef.current = null;
            return;
        }
        const durationSecs = Math.max(1, foregroundTaskRow.duration_mins * 60);
        const breakIntervalSecs = Math.max(60, foregroundTaskRow.break_interval_mins * 60);
        if (
            durationSecs <= FOREGROUND_BREAK_COUNTDOWN_THRESHOLD_SECS ||
            breakIntervalSecs >= durationSecs
        ) {
            previousForegroundProgressRef.current = {
                taskId: foregroundTaskId,
                value: foregroundProgressEffective,
            };
            return;
        }
        if (foregroundProgressEffective >= durationSecs) {
            previousForegroundProgressRef.current = {
                taskId: foregroundTaskId,
                value: foregroundProgressEffective,
            };
            return;
        }
        const prev =
            previousForegroundProgressRef.current?.taskId === foregroundTaskId
                ? previousForegroundProgressRef.current.value
                : foregroundProgressEffective;
        const nextBoundary = (Math.floor(prev / breakIntervalSecs) + 1) * breakIntervalSecs;
        previousForegroundProgressRef.current = {
            taskId: foregroundTaskId,
            value: foregroundProgressEffective,
        };
        if (nextBoundary >= durationSecs) return;
        if (prev < nextBoundary && foregroundProgressEffective >= nextBoundary) {
            void startForegroundBreakFlow();
        }
    }, [
        foregroundTaskId,
        foregroundTaskRow,
        foregroundProgressEffective,
        startForegroundBreakFlow,
    ]);

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
                            <div
                                className={
                                    'tasks-panel-todo-column-stack' +
                                    (showDoingCard ? ' tasks-panel-todo-column-stack--with-doing' : '')
                                }
                            >
                                <div
                                    className={
                                        'tasks-panel-doing-slot' +
                                        (doingAnimExpanded ? ' tasks-panel-doing-slot--expanded' : '')
                                    }
                                    onTransitionEnd={onDoingSlotTransitionEnd}
                                >
                                    <div className="tasks-panel-doing-slot-inner">
                                        {doingAnimContent ? (
                                            <div className="tasks-panel-doing-card-wrap">
                                                <div
                                                    className={
                                                        'tasks-panel-column-card tasks-panel-doing-card' +
                                                        (doingCloseDialogOpen
                                                            ? ' tasks-panel-doing-card--dialog-open'
                                                            : '')
                                                    }
                                                    style={{backgroundColor: doingCardBackground}}
                                                >
                                                    <div
                                                        className={
                                                            'tasks-panel-column-head tasks-panel-doing-card-head' +
                                                            (doingCloseDialogOpen
                                                                ? ' tasks-panel-doing-card-head--dialog-open'
                                                                : '')
                                                        }
                                                    >
                                                        
                                                        <h3>
                                                            {!doingCloseDialogOpen ? 
                                                                "Doing: " :
                                                                `Would you like help breaking the task${doingTasksForUi.length > 1 ? 's' : ''} down?`
                                                            }
                                                        </h3>
                                                        <button
                                                            type="button"
                                                            className="floating"
                                                            style={{
                                                                height:"auto", width:"fit-content"
                                                            }}
                                                            aria-label={
                                                                doingCloseDialogOpen
                                                                    ? 'Decline help and reset progress'
                                                                    : 'Close doing tasks'
                                                            }
                                                            onClick={() =>
                                                                doingCloseDialogOpen
                                                                    ? onDoingDialogNo()
                                                                    : setDoingCloseDialogOpen(true)
                                                            }
                                                        >
                                                            <MdClose aria-hidden />
                                                        </button>
                                                    </div>
                                                    <div className="tasks-panel-column-body tasks-panel-doing-card-body">
                                                        <div className="tasks-panel-doing-body-stack">
                                                            <div
                                                                className={
                                                                    'tasks-panel-doing-rows' +
                                                                    (doingCloseDialogOpen
                                                                        ? ' tasks-panel-doing-rows--invisible'
                                                                        : '')
                                                                }
                                                            >
                                                                {doingTasksForUi.map((t) => renderDoingTaskRow(t))}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    {doingCloseDialogOpen ? (
                                                        <div
                                                            className="tasks-panel-doing-dialog tasks-panel-doing-dialog--card-overlay"
                                                            role="dialog"
                                                            aria-modal="true"
                                                            aria-labelledby="tasks-doing-dialog-title"
                                                        >
                                                            <div className="tasks-panel-doing-dialog-actions">
                                                                <button
                                                                    type="button"
                                                                    className="secondary"
                                                                    onClick={onDoingDialogYes}
                                                                >
                                                                    Yes
                                                                </button>
                                                                <button
                                                                    type="button"
                                                                    className="secondary"
                                                                    onClick={onDoingDialogNo}
                                                                >
                                                                    No
                                                                </button>
                                                            </div>
                                                        </div>
                                                    ) : null}
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                </div>
                                <div
                                    ref={todoEntryContainerRef}
                                    className="tasks-panel-column-card tasks-panel-todo-main-card"
                                >
                                <div className="tasks-panel-column-head">
                                    <h3>
                                        To-Do: {todoIncompleteTasks.length}
                                    </h3>
                                </div>
                                <div className="tasks-panel-column-body">
                                    <div ref={todoColumnScrollRef} className="tasks-panel-column-scroll">
                                        {todoIncompleteTasks.map((t) => renderTaskRow(t, 'todo'))}
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
                                                        className="primary"
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
                                                    className="secondary"
                                                    disabled={addTaskBlockedByPending}
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
                                    <h3>
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
            <TaskEditDialog
                open={todoEditTask !== null}
                onClose={() => setTodoEditTask(null)}
                taskId={todoEditTask?.id ?? null}
                sessionToken={session.token ?? undefined}
                userTimeZone={userTimeZone}
                surfaceBackgroundColor={
                    todoEditTask
                        ? safeTaskBackgroundFromColourRaw(todoEditTask.colour_raw)
                        : '#eee'
                }
                onTaskMerged={handleTaskMerged}
                onTaskRemoved={handleTaskRemoved}
                onBoardReload={handleEditBoardReload}
                onStartWork={handleStartWorkFromEdit}
                onError={(msg) => setTasksError(msg)}
            />

            {focusConfirmRow && focusConfirmTaskId !== null ? (
                <TaskForegroundConfirm
                    open
                    onClose={onFocusConfirmClose}
                    panelBackgroundColor={safeTaskBackgroundFromColourRaw(focusConfirmRow.colour_raw)}
                    taskDurationMins={focusConfirmRow.duration_mins}
                    taskProgressSecs={focusConfirmRow.progress_secs}
                    onChooseBackground={onFocusConfirmBackground}
                    onChooseForeground={() => void onFocusConfirmForeground()}
                />
            ) : null}

            {foregroundTaskRow && foregroundTaskId !== null ? (
                <TaskForeground
                    open
                    onPauseToBackground={() => void onForegroundPauseToBackground()}
                    task={{
                        id: foregroundTaskRow.id,
                        name: foregroundTaskRow.name,
                        duration_mins: foregroundTaskRow.duration_mins,
                        colour_raw: foregroundTaskRow.colour_raw,
                    }}
                    panelBackgroundColor={safeTaskBackgroundFromColourRaw(foregroundTaskRow.colour_raw)}
                    countdownTotalSeconds={foregroundBreakSegment.total}
                    countdownProgressSeconds={foregroundBreakSegment.progress}
                    inboxItems={foregroundInboxItems}
                    onInboxItemsChange={setForegroundInboxItems}
                    isBoardWideViewport={isBoardWideViewport}
                    onNeedHelp={() => void onForegroundNeedHelp()}
                    onFinished={() => void onForegroundFinished()}
                />
            ) : null}

            <TaskBreakConfirm
                open={breakConfirmOpen}
                onClose={onBreakConfirmClose}
                completedCount={breakCompletedCount}
                nextTask={breakFlowNextTask}
                isBoardWideViewport={isBoardWideViewport}
                onTakeBreak={onBreakTakeBreak}
                onKeepGoing={onBreakKeepGoing}
            />

            <TaskBreakSetup
                open={breakSetupOpen}
                onClose={onBreakSetupClose}
                onConfirmBreak={onBreakSetupConfirm}
            />

            <TaskBreak
                open={breakRunOpen}
                onClose={onBreakRunClose}
                durationSeconds={breakDurationSecs}
                onNextTask={onBreakNextTask}
            />
        </div>
    );
}
