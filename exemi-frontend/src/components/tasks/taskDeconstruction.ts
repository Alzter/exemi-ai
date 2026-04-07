/**
 * Invoked when the user accepts help breaking down an in-progress task from the Tasks panel.
 * @param unit_id Canvas unit id from the task's assignment (optional); scopes the new chat to that unit.
 */
export function call_task_deconstruction(
    task_id: number,
    task_name: string,
    unit_id?: number | null,
): void {
    if (typeof window === 'undefined') return;
    window.dispatchEvent(
        new CustomEvent('task-deconstruction-request', {
            detail: {
                taskId: task_id,
                taskName: task_name,
                unitId: unit_id ?? null,
            },
        }),
    );
}
