# Exemi Backend
Exemi's so-called business logic is executed in a Python application which is accessed via the frontend through a ReSTful API (FastAPI).
The backend is responsible for persisting user data to a MariaDB database, querying the Canvas API to retrieve students' assignment details, and calling a locally-hosted LLM through Ollama.

## Installation
To set up Exemi's backend, the following steps are required.

### 1. Install MariaDB Server
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

### 2. Create Exemi database and database administrator account
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

### 3. Create a user token encryption key
We also need to create a secret key for the backend to perform user token encryption/decryption using HS256.
Install OpenSSL, then run the following command:

```bash
openssl rand -hex 32
> YOURSECRETKEY
```

### 4. Create an .env file to store the secrets
Finally, we must store the database administrator account credentials and the user token encryption key in an environment variables file.
Create the file in ``exemi-backend/.env`` like so:

```python
DB_USER = "exemi"
DB_PASS = "YOURSTRONGPASSWORD"
DB_HOST = "127.0.0.1"
DB_NAME = "exemi"
SECRET_KEY = "YOURSECRETKEY"
```

## Running
```bash
fastapi dev main.py
```
