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
The simplest way to host the frontend on a Linux web
server is to install [nginx](https://nginx.org/) and
configure it to forward web traffic to Vite. You can
use the following nginx configuration:

```
http {
    server {
        listen 80;
        server_name exemi.au www.exemi.au; # If you have purchased a domain name, you can assign it here
        access_log /var/log/nginx/access.log;
        location / {
            proxy_pass http://localhost:5173;
        }
    }
}
```

You can run the frontend with the usual Vite command,
and nginx will forward any traffic to it.

```bash
nginx
cd exemi-frontend
nix-shell
yarn vite
```

To enable HTTPS access to the frontend, you can use
[Certbot](https://certbot.eff.org/) to automatically
create a Let's Encrypt HTTPS certificate and update
your nginx configuration to include the certificate.
If you have a multi-user Nix installation or NixOS,
you can run the following command to enable HTTPS
access to the web server.

```bash
cd exemi-frontend
sudo su
nix-shell
certbot --nginx
exit
```
