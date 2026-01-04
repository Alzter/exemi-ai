import requests
import json
import pandas as pd
from datetime import datetime
from tzlocal import get_localzone

"""
Decodes Canvas API responses into DataFrames for downstream use.
"""

def parse_iso_timestamps(data : pd.DataFrame) -> pd.DataFrame:
    """
    Replace all string timestamps in a DataFrame with datetime objects.
    All timestamps must comply with ISO-8601.

    Args:
        data (DataFrame): DataFrame containing ISO-8601 string timestamps.

    Returns:
        data (DataFrame): DataFrame containing datetime timestamps.
    """

    # Obtain all columns which can be converted
    # into a timestamp through ugly brute-forcing
    timestamp_columns = []
    for key, value in data.iloc[0].to_dict().items():
        if type(value) is str:
            try:
                datetime.fromisoformat(value)
                timestamp_columns.append(key)
            except:
                pass

    def isotime_to_timestamp(value : str | None, use_local_timezone : bool = True, as_string : bool = False):
        if type(value) is not str: return None
        
        time = datetime.fromisoformat(value)
        if use_local_timezone:
            time = time.astimezone(get_localzone())

        if as_string:
            time = time.strftime("%A, %d %B %Y, %I:%M %p")
            
        return time
    
    for column in timestamp_columns:
        data[column] = data[column].map(isotime_to_timestamp)

    return data

def process_canvas_dataframe(response : pd.DataFrame) -> pd.DataFrame:
    response = parse_iso_timestamps(response) # Convert string timestamps to object
    response = response.dropna(axis=1, how="all") # Drop columns with entirely NA values
    return response
    
def decode_canvas_response(response : requests.Response | list[dict]) -> pd.DataFrame:
    """
    Converts raw Canvas API response into a DataFrame for downstream use,
    or raises Exception if the response is invalid.

    Args:
        response (Response | dict): The API response obtained from Canvas.

    Returns:
        response_data (DataFrame): The response data.
    """

    if type(response) is requests.Response:
        if not response.ok: response.raise_for_status()

        # Canvas API will always respond in JSON format,
        # but we obtain the response in bytes, so it
        # must be decoded into a raw string and then
        # encoded into a JSON object.
        
        response = response.content.decode('utf-8')
        
        response = json.loads(response)
    
    if not response:
        # Empty response
        return pd.DataFrame([])
    
    if type(response) is not list: response = [response]
    
    response = pd.DataFrame(response)

    response = process_canvas_dataframe(response)

    return response
