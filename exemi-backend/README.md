# Exemi Backend
Exemi's so-called business logic is executed in a Python application which is accessed via the frontend through a ReSTful API (FastAPI).
The backend is responsible for persisting user data to a MariaDB database, querying the Canvas API to retrieve students' assignment details, and calling a locally-hosted LLM through Ollama.

## Installation
To set up Exemi's backend, the following steps are required.

### 1. Install Nix packages
```bash
cd exemi-backend
nix-build shell.nix
```

### 2. Install Meta Llama 3.1 with Ollama
Exemi's backend requires access to a locally-hosted LLM to operate.
Exemi uses Meta Llama 3.1 as its LLM of choice, which you can install locally using Ollama.
To install the LLM, run this command:

```bash
cd exemi-backend
nix-shell
ollama serve | ollama pull llama3.1:8b
exit
```

This command will host Ollama and install Meta Llama 3.1.
Note that Ollama server **will not terminate** when the LLM has finished installing, so you must manually stop it with CTRL+C once the installation is finished.

### 3. Install MariaDB Server
Install MariaDB onto your system using the following commands:

#### Debian/Ubuntu:
```bash
sudo apt install mariadb-server mariadb-client galera-4
```
#### Red Hat/CentOS/Fedora
```bash
sudo dnf install mariadb mariadb-server
```

#### NixOS:
Add into ``/etc/nixos/configuration.nix``:
```
services.mysql = {
    enable = true;
    package = pkgs.mariadb;
};
```
Then rebuild your system configuration with:
```bash
sudo nixos-rebuild switch
```

### 4. Create Exemi database and database administrator account
Once MariaDB is installed, login to MariaDB as "root" using the root password you set during the installation.

```bash
mariadb -u root -p
> Enter password:
```

Next, create the Exemi database:

```mysql
CREATE DATABASE exemi;
```

Next, create a new MariaDB account with administrator privileges for the Exemi database like so:
**Replace "YOURSTRONGPASSWORD" with a password of your choosing.**

```mysql
CREATE USER 'exemi'@'localhost' IDENTIFIED BY 'YOURSTRONGPASSWORD';
GRANT ALL PRIVILEGES ON exemi.* TO 'exemi'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Create a user token encryption key
You also need to create a secret key for the backend to perform user token encryption/decryption using HS256.
Install OpenSSL, then run the following command:

```bash
openssl rand -hex 32
> YOURSECRETKEY
```

### 6. Create an .env file to store the secrets
Finally, you must store the database administrator account credentials and the user token encryption key in an environment variables file.
Create the file in ``exemi-backend/.env`` like so:

```python
DB_USER = "exemi"
DB_PASS = "YOURSTRONGPASSWORD"
DB_HOST = "127.0.0.1"
DB_NAME = "exemi"
SECRET_KEY = "YOURSECRETKEY"
LLM_MODEL = "llama3.1:8b"
LLM_API_URL = "http://localhost:11434"
```

## Running
### Development
```bash
cd exemi-backend
nix-shell
fastapi dev main.py --host 0.0.0.0
```

### Production
```bash
cd exemi-backend
nix-shell
fastapi run main.py
```
