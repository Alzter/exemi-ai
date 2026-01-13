from fastapi import FastAPI
from llama_cpp import Llama
from huggingface_hub import hf_hub_download
import os

MODEL_REPO = "TheBloke/Llama-2-7B-Chat-GGUF"
MODEL_FILE = "llama-2-7b-chat.Q4_K_M.gguf"

model_path = hf_hub_download(
    repo_id=MODEL_REPO,
    filename=MODEL_FILE,
    cache_dir=os.getenv("HF_HOME", "~/.cache/huggingface"),
)

llm = Llama(
    model_path=model_path,
    n_ctx=4096,
    n_threads=8,
)

app = FastAPI()

@app.post("/generate")
def generate(prompt: str):
    result = llm(
        prompt,
        max_tokens=256,
        stop=["</s>"],
    )
    return {"text": result["choices"][0]["text"]}
