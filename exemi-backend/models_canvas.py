from pydantic import BaseModel
from datetime import datetime
from typing import Literal

class CanvasTerm(BaseModel):
    id : int
    name : str
    start_at : datetime | None = None
    end_at : datetime | None = None

class CanvasUnit(BaseModel):
    id : int
    name : str
    original_name : str | None = None
    enrollment_term_id : int
    term : CanvasTerm
    # Weight final grade based on assignment group percentages
    apply_assignment_group_weights : bool

class CanvasAssignment(BaseModel):
    id : int
    name : str
    description : str | None
    due_at : datetime | None
    points_possible : float | None
    assignment_group_id : int
    # Group category ID is only set if the assignment is group-based
    group_category_id : int | None
    # If this is a group assignment, boolean flag indicating whether or not
    # students will be graded individually.
    grade_group_students_individually : bool
    # If true, the assignment's points don't count towards final mark
    omit_from_final_grade : bool

class CanvasSubmission(BaseModel):
    # If multiple submissions have been made, this is the attempt number.
    attempt : int | None
    late : bool
    # If true, this assignment will not count towards the user's grade
    excused : bool | None
    # The raw score for the assignment submission.
    # score : float | None
    # The timestamp when the assignment was submitted, if an actual submission has been made.
    submitted_at : datetime | None
    # The current status of the submission.
    # Legal values: "submitted", "unsubmitted", "graded", "pending", "pending_review"
    workflow_state : str # Literal["submitted", "unsubmitted", "graded", "pending", "pending_review"]

class CanvasAssignmentWithSubmission(CanvasAssignment):
    submission : CanvasSubmission

class CanvasAssignmentGroup(BaseModel):
    id : int
    name : str
    group_weight : float
    assignments : list[CanvasAssignment]
