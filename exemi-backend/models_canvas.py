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

class CanvasAssignmentGroup(BaseModel):
    id : int
    name : str
    group_weight : float 
    assignments : list[CanvasAssignment]
