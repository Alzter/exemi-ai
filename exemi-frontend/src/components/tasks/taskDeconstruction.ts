/**
 * Invoked when the user accepts help breaking down an in-progress task from the Tasks panel.
 */
export function call_task_deconstruction(task_id: number, task_name: string): void {
    if (typeof window === 'undefined') return;
    window.dispatchEvent(
        new CustomEvent('task-deconstruction-request', {
            detail: {
                taskId: task_id,
                taskName: task_name,
            },
        }),
    );
}
