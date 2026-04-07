# Task generation and assignment deltas

## Goal

The `/tasks_generate` flow calls a local LLM to break Canvas assignments into small tasks. That prompt used to always include **every** open assignment (including long descriptions), which is slow and token-heavy.

The backend now:

1. Stores a per-student **snapshot** of the assignment payload at the last **committed** generation (`User.tasks_generation_assignments_snapshot`).
2. On later runs, **diffs** the current assignments against that snapshot and, when possible, sends only **changes** (added / removed / changed assignments).
3. **Skips the LLM** when the diff is empty **and** there are no overdue incomplete tasks.

## Snapshot format

- Same JSON shape as the assignments tool: list of units, each with `assignments` (`AssignmentJSON` in [`routers/curriculum.py`](../routers/curriculum.py)).
- **`days_remaining` is omitted** in the snapshot (stored as `null`). It changes every day without any Canvas change and would force false diffs.

## When the snapshot is updated

- Only after a successful run with **`commit=True`** that applied LLM output (`commit_generated_tasks` in [`routers/tasks.py`](../routers/tasks.py)), the snapshot is rewritten from the current `build_assignments_payload` for that student.
- **`commit=False`**: snapshot is **not** updated (dry run).

## Prompt branches

| Situation | Behaviour |
|-----------|-----------|
| No existing incomplete tasks | Full **ASSIGNMENTS** JSON. |
| Existing tasks but no snapshot yet (legacy) | Full **ASSIGNMENTS** until the first committed generation fills the snapshot. |
| Snapshot + non-empty diff | **ASSIGNMENT_CHANGES** JSON (`added`, `removed`, `changed`) plus **UNITS**. |
| Snapshot + empty diff + overdue incomplete tasks | **UNITS** + short **ASSIGNMENTS** note that Canvas is unchanged; model applies overdue rules only. |
| Snapshot + empty diff + no overdue tasks | **LLM bypass**: return existing tasks as `TaskList` without calling the model. |

## Target student vs admin

Prompt data (units, assignments, snapshot) uses the **target** `User` resolved by path `username`. The authenticated user is only used for authorisation (self or admin).

## Database migration

`SQLModel.metadata.create_all` does **not** add columns to existing databases. For an existing deployment, add the column manually, for example (MySQL/MariaDB; adjust table name if your metadata differs):

```sql
ALTER TABLE user ADD COLUMN tasks_generation_assignments_snapshot TEXT NULL;
```

For the task edit UI (`task_break_interval_mins` on `User` in `models.py`), existing databases may need:

```sql
ALTER TABLE user ADD COLUMN task_break_interval_mins INT NULL;
```

## Code map

- [`llm_api.py`](../llm_api.py) — `prepare_task_generation`, bypass vs `invoke`, `CreateTasksForUserResult`.
- [`routers/llm_prompt.py`](../routers/llm_prompt.py) — `prepare_task_generation`, prompt text, `/prompt/tasks/{username}` when bypassing.
- [`routers/curriculum.py`](../routers/curriculum.py) — `build_assignments_payload`, `snapshot_assignments_json`, `compute_assignments_delta`.
- [`routers/tasks.py`](../routers/tasks.py) — `save_tasks_generation_assignments_snapshot`, overdue helper, generate endpoint wiring.
- [`models.py`](../models.py) — `User.tasks_generation_assignments_snapshot`.

## Local Python

Use the project Nix shell when running Python from `exemi-backend`, for example:

`cd exemi-backend && nix-shell --run "python -m pytest …"`
