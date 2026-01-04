from typing import Union

from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer

import requests

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/user_exists/")
async def user_exists(provider : str, access_token : str):
    response = requests.get(f"https://{provider}.instructure.com/api/v1/users/self", params={
        "access_token":access_token,
    })
    return response.status_code == 200

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
