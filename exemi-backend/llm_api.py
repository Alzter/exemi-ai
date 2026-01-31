from fastapi import APIRouter, Depends, HTTPException, Query
import litellm
from litellm import completion
import instructor
from pydantic import BaseModel

# router = APIRouter()
# class User(BaseModel):
#     name: str
#     age: int

MODEL = "llama3.1:8b"
LLM_API_URL = "http://localhost:11434"
client = instructor.from_provider(f"ollama/{MODEL}")

# @router.get("/llm/chat{messageb}")
async def chat(messages : list[dict]) -> str:
    try:
        response = completion(
            model = f"ollama_chat/{MODEL}",
            api_base=LLM_API_URL,
            messages=messages
        )
        
        response_message = response.choices[0].message.content

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail= f"Error generating LLM response. Detail: {str(e)}"
        )

    return response_message

# @router.get("/llm/test_instructor")
# async def test_instructor():
#     user = client.create(
#         response_model=User,
#         messages=[{"role": "user", "content": "John Doe is 30 years old."}],
#     )
#     return user
