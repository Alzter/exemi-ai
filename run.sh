run_frontend() {
  cd exemi-frontend
  nix-shell --run 'yarn vite'
}

run_backend() {
  cd exemi-backend
  nix-shell --run 'fastapi dev main.py'
}

run_llm() {
  cd exemi-backend
  nix-shell --run 'ollama serve'
}

run() {
  run_frontend & run_backend & run_llm
}

run
