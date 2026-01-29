run_frontend() {
  cd exemi-frontend
  npx vite
}

run_backend() {
  cd exemi-backend
  fastapi dev main.py
}

run_llm() {
  ollama serve
}

run() {
  run_frontend & run_backend & run_llm
}

run
