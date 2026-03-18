# Exemi
Exemi is an AI-powered study assistance tool designed to help students with ADHD improve their planning and time management skills.
It utilises publicly available large language models (LLMs) to provide study assistance tailored to students' unique conditions.
It also integrates with Canvas LMS to automatically retrieve students' assignment information.

## Dependencies
To run Exemi, you will need the [Nix](https://nixos.org/) package manager installed.
Nix works best on Linux systems: compatibility is not guaranteed for Windows or Mac systems.

## Installation
Clone this repository, then open ``bash`` and ``cd`` into the install directory.

### Frontend
To install the dependencies for the frontend, follow the steps [here](exemi-frontend/README.md#) to install all the dependencies.

### Backend
To install the dependencies for the backend, follow the steps [here](exemi-backend/README.md#) to install all the dependencies.

## Running
Once you have installed the dependencies for the frontend and the backend,
you can run them both simultaneously like this:

```bash
sh run.sh
```
To stop Exemi, terminate the process with CTRL+C.

## Architecture Design
<img width="800" alt="image" src="https://github.com/user-attachments/assets/65631107-39b0-48f6-8e63-89080216781e" />

### Presentation Layer
Provides user interface

- **React + Vite Web App**
  - Communicates with backend via API
  - Receives traffic through port forwarding from NGINX

- **NGINX**
  - Web Server
  - Handles port forwarding to frontend
  
### Service Layer
Defines API endpoints and response templates and
communicates with Canvas and locally hosted LLM

- **Python FastAPI**
  - **Main API entrypoint**
    - Handles incoming requests
    - Routes to internal services

  - **LangChain**
    - Handles LLM chats and tool calling

  - **SQLModel**
    - Interfaces with database
    - Performs CRUD operations

- **External Integration**
  - **Canvas LMS API**
    - Provides **Curriculum Information**

### Persistence Layer
Specifies database schema and performs CRUD operations

- Managed via:
  - **SQLModel**

### Data Layer
Stores data entries

- **MariaDB**
  - Primary database

### AI Layer
Locally hosts open-weights large language models (LLM) for text generation

- **Ollama API**
  - Serves LLM requests

- **Qwen 3 14B**
  - Model used for text generation

### Data Flow Overview

1. User interacts with **React + Vite Web App**
2. Requests go through **NGINX** (port forwarding)
3. Backend handled by **FastAPI**
4. FastAPI:
   - Queries **Canvas LMS API** for curriculum data
   - Uses **LangChain + Ollama (Qwen 3 14B)** for AI tasks
   - Reads/writes data via **SQLModel → MariaDB**
5. Responses returned to frontend

## License
Exemi is licensed under the GNU General Public License v3, meaning you are
free to modify or redistribute it as you see fit so long as you retain the same license.
