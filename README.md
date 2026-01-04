# Exemi

## Supported Platforms
Currently, only NixOS is supported for running Exemi, however other platforms are planned soon.

## Installation
To install Exemi, you must clone this repository and then install all dependencies.

### NixOS
Clone this repository and ``cd`` into the local folder. Run this command to install all dependencies:

```bash
nix-build shell.nix
```

## Running 
### NixOS
To start Exemi, run this command:
```bash
nix-shell
sh run.sh
```
To shut down Exemi, terminate the process with CTRL+C.

## Architecture Design
Frontend: Vite + React
Middleware: FastAPI
Backend: Python
Database: MariaDB
