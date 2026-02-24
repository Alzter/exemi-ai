from pydantic import BaseModel
from datetime import datetime

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

class CanvasAssignmentGroup(BaseModel):
    id : int
    name : str
    group_weight : float 
    assignments : list[CanvasAssignment]
