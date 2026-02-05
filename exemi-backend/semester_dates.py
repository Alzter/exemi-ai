from datetime import datetime
from models_canvas import CanvasTerm
import re

SEMESTER_OVERRIDES = {
    (2022, 1): (date(2022, 2, 28), date(2022, 6, 19)),
    (2022, 2): (date(2022, 7, 25), date(2022, 11, 20)),
    (2024, 2): (date(2024, 7, 29), date(2024, 11, 24)),
}

teaching_period_extractor = re.compile(r"(\d*)\sSemester\s(\d*)")

def get_teaching_period(term_name : str) -> tuple[int, int] | None:
    """
    Given a university semester name string, return the teaching period.

    Args:
        term_name (str): "2022 Semester 1"
    
    Returns:
        tuple[int, int]: 2022, 1
    """
    match = teaching_period_extractor.search(term_name)
    if not match: return None
    if match:
        return (int(match.group(1)), int(match.group(2)))

def rectify_term_date(term : CanvasTerm):
    """
    Given a CanvasTerm object, correct the start and end
    dates to be consistent with Swinburne's official
    academic calendar.

    Args:
        term (CanvasTerm): The CanvasTerm to correct.
    
    Returns:
        fixed_term (CanvasTerm): The CanvasTerm with dates corrected.
    """
    
    teaching_period : tuple[int,int] | None = get_teaching_period(term.name)
    if not teaching_period: return term

    rectified_dates = SEMESTER_OVERRIDES.get(teaching_period)
    if not rectified_dates: return term

    start_date, end_date = rectified_dates

    new_term = term.copy()
    new_term.start_at = start_date
    new_term.end_at = end_date
    
    return new_term
