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
<img width="800" alt="image" src="https://github.com/user-attachments/assets/1b5619cd-0e62-4f50-a703-f074322151dd" />

## License
Exemi is licensed under the GNU General Public License v3, meaning you are
free to modify or redistribute it as you see fit so long as you retain the same license.
