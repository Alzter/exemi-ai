import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {
    MdAssignment,
    MdCheckBox,
    MdCheckBoxOutlineBlank,
    MdPause,
    MdPlayArrow,
    MdToday,
    MdDelete,
} from 'react-icons/md';
import {DialogBox} from '../ui/DialogBox';
import {safeTaskBackgroundFromColourRaw, utcIsoForLocalCalendarDate} from '../../utils/taskBoardUtils';

const backendURL = import.meta.env.VITE_BACKEND_API_URL;

export type TaskPublicApi = {
    id: number;
    name: string;
    description: string;
    duration_mins: number;
    break_interval_mins: number;
    assignment_id: number | null;
    assignment?: {id: number; name: string | null} | null;
    due_at: string;
    completed: boolean;
    progress_secs: number;
    colour_raw: string | null;
    created_at?: string;
};

export type TaskPublicRowPatch = Partial<{
    name: string;
    description: string;
    duration_mins: number;
    break_interval_mins: number;
    assignment_id: number | null;
    due_at: string;
    completed: boolean;
    progress_secs: number;
    colour_raw: string | null;
    created_at: string;
    calendarDateISO: string;
}> & {id: number};

function localCalendarISOFromDueAtUtc(isoUtc: string, timeZone: string): string {
    const d = new Date(isoUtc);
    return new Intl.DateTimeFormat('en-CA', {
        timeZone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
    }).format(d);
}

function formatChipDate(isoUtc: string, timeZone: string): string {
    const d = new Date(isoUtc);
    return d.toLocaleDateString('en-US', {month: 'long', day: 'numeric', timeZone});
}

export function mergeTaskFromApiResponse(
    api: TaskPublicApi,
    timeZone: string,
): TaskPublicRowPatch {
    return {
        id: api.id,
        name: api.name,
        description: api.description,
        duration_mins: api.duration_mins,
        break_interval_mins: api.break_interval_mins,
        assignment_id: api.assignment_id,
        due_at: api.due_at,
        completed: api.completed,
        progress_secs: api.progress_secs,
        colour_raw: api.colour_raw,
        ...(api.created_at != null ? {created_at: api.created_at} : {}),
        calendarDateISO: localCalendarISOFromDueAtUtc(api.due_at, timeZone),
    };
}

type AssignmentOption = {id: number; name: string | null};

export type TaskEditDialogProps = {
    open: boolean;
    onClose: () => void;
    /** Board row snapshot; omitted fields loaded via GET /task/{id}. */
    taskId: number | null;
    sessionToken: string | undefined;
    userTimeZone: string;
    surfaceBackgroundColor: string;
    onTaskMerged: (patch: TaskPublicRowPatch) => void;
    onTaskRemoved: (taskId: number) => void;
    onBoardReload: () => void;
    onStartWork: (taskId: number) => void;
    onError: (message: string) => void;
};

export function TaskEditDialog({
    open,
    onClose,
    taskId,
    sessionToken,
    userTimeZone,
    surfaceBackgroundColor,
    onTaskMerged,
    onTaskRemoved,
    onBoardReload,
    onStartWork,
    onError,
}: TaskEditDialogProps) {
    const [detail, setDetail] = useState<TaskPublicApi | null>(null);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [assignments, setAssignments] = useState<AssignmentOption[]>([]);

    const [titleEditing, setTitleEditing] = useState(false);
    const [titleDraft, setTitleDraft] = useState('');
    const titleInputRef = useRef<HTMLInputElement>(null);
    const dateInputRef = useRef<HTMLInputElement>(null);

    const [descDraft, setDescDraft] = useState('');
    const [durDraft, setDurDraft] = useState('');
    const [breakDraft, setBreakDraft] = useState('');

    const applyApiToState = useCallback(
        (api: TaskPublicApi) => {
            setDetail(api);
            setTitleDraft(api.name);
            setDescDraft(api.description ?? '');
            setDurDraft(String(api.duration_mins));
            setBreakDraft(String(api.break_interval_mins));
        },
        [],
    );

    const patchTask = useCallback(
        async (id: number, body: Record<string, unknown>): Promise<TaskPublicApi | null> => {
            const token = sessionToken;
            if (!token) return null;
            const res = await fetch(`${backendURL}/task/${id}`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const t = await res.text();
                onError(t || res.statusText || 'Could not update task.');
                return null;
            }
            return (await res.json()) as TaskPublicApi;
        },
        [sessionToken, onError],
    );

    const patchUserTaskBreakInterval = useCallback(
        async (taskBreakIntervalMins: number): Promise<number | null> => {
            const token = sessionToken;
            if (!token) return null;
            const res = await fetch(`${backendURL}/users/self`, {
                method: 'PATCH',
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    Accept: 'application/json',
                },
                body: JSON.stringify({task_break_interval_mins: taskBreakIntervalMins}),
            });
            if (!res.ok) {
                const t = await res.text();
                onError(t || res.statusText || 'Could not update break interval.');
                return null;
            }
            const data = (await res.json()) as {task_break_interval_mins?: number | null};
            return data.task_break_interval_mins || 25;
        },
        [sessionToken, onError],
    );

    useEffect(() => {
        if (!open || !taskId || taskId <= 0 || !sessionToken) {
            setDetail(null);
            setLoadError(null);
            setLoading(true);
            setTitleEditing(false);
            setDeleteOpen(false);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setLoadError(null);

        fetch(`${backendURL}/task/${taskId}`, {
            headers: {Authorization: `Bearer ${sessionToken}`, Accept: 'application/json'},
        })
            .then(async (res) => {
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(text || res.statusText);
                }
                return res.json() as Promise<TaskPublicApi>;
            })
            .then((api) => {
                if (cancelled) return;
                applyApiToState(api);
                onTaskMerged(mergeTaskFromApiResponse(api, userTimeZone));
            })
            .catch((e: unknown) => {
                if (cancelled) return;
                setLoadError(e instanceof Error ? e.message : 'Could not load task.');
            })
            .finally(() => {
                // setLoadError('Could not load task.');
                if (!cancelled) setLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [open, taskId, sessionToken, userTimeZone, applyApiToState, onTaskMerged]);

    useEffect(() => {
        if (!open || !sessionToken) {
            setAssignments([]);
            return;
        }
        let cancelled = false;
        const params = new URLSearchParams({
            exclude_complete: 'false',
            exclude_no_due_date: 'false',
            limit: '100',
            offset: '0',
        });
        fetch(`${backendURL}/assignments?${params}`, {
            headers: {Authorization: `Bearer ${sessionToken}`, Accept: 'application/json'},
        })
            .then(async (res) => {
                if (!res.ok) return [];
                const raw = (await res.json()) as AssignmentOption[];
                return Array.isArray(raw) ? raw : [];
            })
            .then((list) => {
                if (!cancelled) setAssignments(list);
            })
            .catch(() => {
                if (!cancelled) setAssignments([]);
            });
        return () => {
            cancelled = true;
        };
    }, [open, sessionToken]);

    useEffect(() => {
        if (!open || deleteOpen) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [open, deleteOpen, onClose]);

    useEffect(() => {
        if (titleEditing) titleInputRef.current?.focus();
    }, [titleEditing]);

    const panelBg =
        detail !== null ? safeTaskBackgroundFromColourRaw(detail.colour_raw) : surfaceBackgroundColor;

    const persistAndMerge = useCallback(
        async (body: Record<string, unknown>) => {
            if (!detail || !taskId) return;
            const next = await patchTask(taskId, body);
            if (!next) return;
            applyApiToState(next);
            onTaskMerged(mergeTaskFromApiResponse(next, userTimeZone));
        },
        [detail, taskId, patchTask, applyApiToState, onTaskMerged, userTimeZone],
    );

    const onTitleBlur = useCallback(async () => {
        setTitleEditing(false);
        if (!detail) return;
        const next = titleDraft.trim();
        if (next === '' || next === detail.name) {
            setTitleDraft(detail.name);
            return;
        }
        await persistAndMerge({name: next});
    }, [detail, titleDraft, persistAndMerge]);

    const onDescBlur = useCallback(async () => {
        if (!detail) return;
        const next = descDraft;
        if (next === detail.description) return;
        await persistAndMerge({description: next});
    }, [detail, descDraft, persistAndMerge]);

    const onDurBlur = useCallback(async () => {
        if (!detail) return;
        const n = Number.parseInt(durDraft, 10);
        if (!Number.isFinite(n) || n < 1) {
            setDurDraft(String(detail.duration_mins));
            return;
        }
        if (n === detail.duration_mins) return;
        await persistAndMerge({duration_mins: n});
    }, [detail, durDraft, persistAndMerge]);

    const onBreakBlur = useCallback(async () => {
        if (!detail) return;
        const n = Number.parseInt(breakDraft, 10);
        if (!Number.isFinite(n) || n < 1) {
            setBreakDraft(String(detail.break_interval_mins));
            return;
        }
        if (n === detail.break_interval_mins) return;
        const effective = await patchUserTaskBreakInterval(n);
        if (effective === null) return;
        const next: TaskPublicApi = {...detail, break_interval_mins: effective};
        applyApiToState(next);
        onTaskMerged(mergeTaskFromApiResponse(next, userTimeZone));
        onBoardReload();
    }, [
        detail,
        breakDraft,
        patchUserTaskBreakInterval,
        applyApiToState,
        onTaskMerged,
        userTimeZone,
        onBoardReload,
    ]);

    const onToggleComplete = useCallback(async () => {
        if (!detail || !taskId) return;
        const next = !detail.completed;
        setDetail((d) =>
            d ? {...d, completed: next, progress_secs: next ? 0 : d.progress_secs} : d,
        );
        const api = await patchTask(
            taskId,
            next ? {completed: true, progress_secs: 0} : {completed: false},
        );
        if (!api) {
            setDetail((d) =>
                d
                    ? {...d, completed: detail.completed, progress_secs: detail.progress_secs}
                    : d,
            );
            return;
        }
        applyApiToState(api);
        onTaskMerged(mergeTaskFromApiResponse(api, userTimeZone));
    }, [detail, taskId, patchTask, applyApiToState, onTaskMerged, userTimeZone]);

    const dateISOValue = detail
        ? localCalendarISOFromDueAtUtc(detail.due_at, userTimeZone)
        : '';

    const onDateChange = useCallback(
        async (e: React.ChangeEvent<HTMLInputElement>) => {
            const v = e.target.value;
            if (!v || !detail) return;
            const due = utcIsoForLocalCalendarDate(v, userTimeZone);
            await persistAndMerge({due_at: due});
            onBoardReload();
        },
        [detail, persistAndMerge, userTimeZone, onBoardReload],
    );

    const onAssignmentChange = useCallback(
        async (e: React.ChangeEvent<HTMLSelectElement>) => {
            const v = e.target.value;
            const assignment_id = v === '' ? null : Number(v);
            if (assignment_id !== null && !Number.isFinite(assignment_id)) return;
            if (assignment_id === detail?.assignment_id) return;
            await persistAndMerge({assignment_id});
        },
        [detail?.assignment_id, persistAndMerge],
    );

    const onStartClick = useCallback(async () => {
        if (!detail || !taskId) return;
        const secs = Math.max(1, detail.progress_secs || 0);
        const api = await patchTask(taskId, {progress_secs: secs});
        if (!api) return;
        applyApiToState(api);
        onTaskMerged(mergeTaskFromApiResponse(api, userTimeZone));
        onStartWork(taskId);
        onClose();
    }, [detail, taskId, patchTask, applyApiToState, onTaskMerged, onStartWork, onClose]);

    const onConfirmDelete = useCallback(async () => {
        if (!taskId || !sessionToken) return;
        setDeleting(true);
        try {
            const res = await fetch(`${backendURL}/task/${taskId}`, {
                method: 'DELETE',
                headers: {Authorization: `Bearer ${sessionToken}`, Accept: 'application/json'},
            });
            if (!res.ok) {
                const t = await res.text();
                onError(t || 'Could not delete task.');
                return;
            }
            onTaskRemoved(taskId);
            setDeleteOpen(false);
            onClose();
        } finally {
            setDeleting(false);
        }
    }, [taskId, sessionToken, onError, onTaskRemoved, onClose]);

    const showBreak = detail !== null && detail.duration_mins > 25;

    const assignmentSelectOptions = useMemo(() => {
        const byId = new Map<number, AssignmentOption>();
        for (const a of assignments) {
            byId.set(a.id, a);
        }
        if (detail?.assignment_id != null && !byId.has(detail.assignment_id)) {
            const label =
                detail.assignment?.name?.trim() || `Assignment ${detail.assignment_id}`;
            byId.set(detail.assignment_id, {id: detail.assignment_id, name: label});
        }
        return [...byId.values()];
    }, [assignments, detail?.assignment_id, detail?.assignment]);

    const overflowMenu = (
        <button
            type="button"
            className="floating"
            aria-label="Delete task"
            onClick={() => setDeleteOpen(true)}
        >
            <MdDelete aria-hidden />
        </button>
    );

    // Don't display dialog box until content is ready
    if (loading) return null;

    return (
        <>
            <DialogBox
                open={open && taskId !== null && taskId > 0}
                onClose={onClose}
                closeOnEscape={false}
                beforeClose={overflowMenu}
                aria-label="Edit task"
                panelClassName="task-edit-dialog-panel"
                panelStyle={{
                    width: 'min(650px, calc(100vw - 2rem))',
                    minHeight: 500,
                    maxHeight: 'min(90vh, 860px)',
                    borderRadius: 8,
                    backgroundColor: panelBg,
                    color: '#1a1a1a',
                }}
            >
                {!loading && !loadError && detail ? (
                    
                    <div className="dialog-panel-title">
                        <button
                            type="button"
                            className="checkbox"
                            aria-label={detail.completed ? 'Mark incomplete' : 'Mark complete'}
                            onClick={() => void onToggleComplete()}
                        >
                            {detail.completed ? (
                                <MdCheckBox aria-hidden />
                            ) : (
                                <MdCheckBoxOutlineBlank aria-hidden />
                            )}
                        </button>

                        {titleEditing ? (
                            <input
                                ref={titleInputRef}
                                // className="task-edit-dialog-title-input"
                                value={titleDraft}
                                aria-label="Task title"
                                onChange={(e) => setTitleDraft(e.target.value)}
                                onBlur={() => void onTitleBlur()}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        e.preventDefault();
                                        (e.target as HTMLInputElement).blur();
                                    }
                                }}
                            />
                        ) : (
                            <h3
                                role="button"
                                tabIndex={0}
                                onClick={() => {
                                    setTitleDraft(detail.name);
                                    setTitleEditing(true);
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        setTitleDraft(detail.name);
                                        setTitleEditing(true);
                                    }
                                }}
                            >
                                {detail.name}
                            </h3>
                        )}
                    </div>
                ) : null}

                {loading || loadError ? 
                <div className="dialog-panel-body" style={{
                    alignItems:"center",
                    justifyContent:"center"
                }}>
                    {loadError ? 
                    <p>{loadError}</p> : <div className='loading-spinner'/>}
                </div> : 
                <div className="dialog-panel-body" style={{paddingLeft:60}}>
                    {!loading && !loadError && detail ? (
                        <>
                            <div className="task-edit-duration-row">
                                <input
                                    type="number"
                                    className="short"
                                    // className="task-edit-number-input"
                                    min={1}
                                    max={24 * 60}
                                    value={durDraft}
                                    aria-label="Duration in minutes"
                                    onChange={(e) => setDurDraft(e.target.value)}
                                    onBlur={() => void onDurBlur()}
                                />
                                <span>minutes</span>
                                {showBreak ? (
                                    <div className="task-edit-break-group">
                                        <MdPause aria-hidden/>
                                        <span>Break every</span>
                                        <input
                                            type="number"
                                            className="short"
                                            min={1}
                                            max={240}
                                            value={breakDraft}
                                            aria-label="Break every N minutes"
                                            onChange={(e) => setBreakDraft(e.target.value)}
                                            onBlur={() => void onBreakBlur()}
                                        />
                                        <span>minutes</span>
                                    </div>
                                ) : null}
                            </div>

                            <label htmlFor="task-edit-desc">
                                Description
                            </label>
                            <textarea
                                id="task-edit-desc"
                                style={{flexGrow:1}}
                                // className="task-edit-description"
                                value={descDraft}
                                placeholder="What steps are needed to complete this task?"
                                onChange={(e) => setDescDraft(e.target.value)}
                                onBlur={() => void onDescBlur()}
                            />

                            <div className="task-edit-chips-row">
                                <input
                                    ref={dateInputRef}
                                    type="date"
                                    className="task-edit-date-native"
                                    value={dateISOValue}
                                    onChange={(e) => void onDateChange(e)}
                                    aria-hidden
                                    tabIndex={-1}
                                />
                                <button
                                    type="button"
                                    className="chip"
                                    onClick={() => {
                                        const el = dateInputRef.current;
                                        if (el && 'showPicker' in el && typeof el.showPicker === 'function') {
                                            el.showPicker();
                                        } else {
                                            el?.click();
                                        }
                                    }}
                                >
                                    <MdToday aria-hidden />
                                    {formatChipDate(detail.due_at, userTimeZone)}
                                </button>

                                <div
                                    className="chip"
                                    style={{width:"100%"}}
                                >
                                    <MdAssignment
                                        aria-hidden
                                    />
                                    <select
                                        // style={{flex: '1 1 0', minWidth: 0}}
                                        aria-label="Assignment"
                                        value={detail.assignment_id ?? ''}
                                        onChange={(e) => void onAssignmentChange(e)}
                                    >
                                        <option value="">No Assignment</option>
                                        {assignmentSelectOptions.map((a) => (
                                            <option key={a.id} value={a.id}>
                                                {a.name?.trim() || `Assignment ${a.id}`}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <button
                                type="button"
                                className="primary"
                                onClick={() => void onStartClick()}
                            >
                                <MdPlayArrow aria-hidden />
                                Start {detail.duration_mins} minute
                                {detail.duration_mins === 1 ? '' : 's'}
                            </button>
                        </>
                    ) : null}
                </div>
                }
            </DialogBox>

            <DialogBox
                open={deleteOpen}
                onClose={() => setDeleteOpen(false)}
                aria-label="Delete task"
                backdropClassName="dialog-backdrop--elevated"
                panelStyle={{
                    width: 'min(360px, calc(100vw - 2rem))',
                    borderRadius: 8,
                    backgroundColor: '#fff',
                    border: '2px solid rgba(0,0,0,0.14)',
                }}
            >
                <div className="dialog-panel-title">
                <h3>Delete this task?</h3>
                </div>
                <div className="dialog-panel-body">
                    <div className="double-column-buttons">
                        <button
                            type="button"
                            className="secondary"
                            onClick={() => setDeleteOpen(false)}
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            className="secondary"
                            disabled={deleting}
                            onClick={() => void onConfirmDelete()}
                        >
                            <MdDelete/>
                            {deleting ? 'Deleting…' : 'Delete'}
                        </button>
                    </div>
                </div>
            </DialogBox>
        </>
    );
}
