# Exemi
Exemi is an AI-powered study assistance tool designed to help students with ADHD improve their planning and time management skills.
It utilises open-source large language models (LLMs) to provide study assistance tailored to students' unique conditions.
It also integrates with Canvas LMS to automatically retrieve students' assignment information.

## Dependencies
To run Exemi, you will need the [Nix](https://nixos.org/) package manager installed.
Nix works best on Linux systems: compatibility is not guaranteed for Windows or Mac systems.

## Installation
Clone this repository, then open ``bash`` and ``cd`` into the install directory.
Run the following command to install all dependencies for Exemi.
```bash
nix-build shell.nix
```

## Running
To start Exemi, run:
```bash
nix-shell
sh run.sh
```
To stop Exemi, terminate the process with CTRL+C.

## Architecture Design
<img width="800" alt="image" src="https://github.com/user-attachments/assets/ada5906e-5184-4c89-9a2f-457d33b02276" />

## License
Exemi is licensed under the GNU General Public License v3, meaning you are free to modify or redistribute it as you see fit so long as you retain the same license.
