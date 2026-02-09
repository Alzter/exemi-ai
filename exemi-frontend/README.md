# Exemi Frontend
Exemi's frontend is powered by a Vite + React app.

## Installation
```bash
cd exemi-frontend
nix-build shell.nix
nix-shell
yarn install
exit
```

## Configuration
To change the backend URL, modify ``exemi_frontend/.env``:
```
VITE_BACKEND_API_URL = "http://127.0.0.1:8000"
```

## Running
### Development
```bash
cd exemi-frontend
nix-shell
yarn vite
```

### Production
```bash
cd exemi-frontend
nix-shell
yarn vite --host
```
