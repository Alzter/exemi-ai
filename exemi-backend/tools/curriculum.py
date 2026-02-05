from ..models import User
from ..models_canvas import CanvasAssignment
from ..dependencies import get_current_user, get_current_magic
from ..routers.canvas import canvas_get_all_assignments
from fastapi import Depends, HTTPException

async def get_assignments(
    user : User = Depends(get_current_user),
    magic : str = Depends(get_current_magic)
) -> str:
    """
    Obtains the user's assignments.
    """

    assignments : list[CanvasAssignment] = await canvas_get_all_assignments(user=user, magic=magic)

    return str(assignments)
