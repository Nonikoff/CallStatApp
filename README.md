# Asterisk Call Statistics API (CallStatApp)

A small Flask API that aggregates call statistics from one or more Asterisk CDR MySQL databases. It exposes endpoints to get per-extension call time summaries and Answer-Seizure Ratio (ASR) by destination country code.

Updated: 2025-12-02

## Overview

- Language: Python 3
- Framework: Flask (WSGI with Gunicorn in production)
- DB Client: PyMySQL
- Config: `.env` via `python-dotenv`
- Container: Dockerfile provided (python:3.10-slim)

The service queries three MySQL hosts (configurable) that contain an `asteriskcdrdb` schema with a `cdr` table. For ASR stats it expects a `country_codes` table and a MySQL function `get_country_code(dst)` to map destination numbers to country codes. Results from all configured databases are combined for the call statistics endpoint and returned per extension.

## Requirements

- Python 3.10+ (3.10 recommended; matches Dockerfile)
- Access to one or more MySQL/MariaDB servers hosting `asteriskcdrdb.cdr`
- Network connectivity from the API host to the DB hosts (TCP 3306 by default)

System packages (Linux) that may be required for building MySQL client headers when installing dependencies:
- `default-libmysqlclient-dev` (Debian/Ubuntu) — already installed in the Docker image

## Project Structure

```
.
├─ app.py            # Flask app with routes and SQL queries
├─ requirements.txt  # Python dependencies
├─ Dockerfile        # Production container image (Gunicorn)
└─ README.md         # This file
```

## Environment Variables

The app reads configuration from a `.env` file in the project root (loaded automatically by `python-dotenv`). Define credentials for up to three databases and the API token:

```
# Database 1
DB1_HOST=host1.example.com
DB1_PORT=3306
DB1_USER=username
DB1_PASSWORD=secret

# Database 2 (optional)
DB2_HOST=host2.example.com
DB2_PORT=3306
DB2_USER=username
DB2_PASSWORD=secret

# Database 3 (optional)
DB3_HOST=host3.example.com
DB3_PORT=3306
DB3_USER=username
DB3_PASSWORD=secret

# API auth
API_TOKEN=your-secure-token
```

Notes
- Do not commit real secrets. Ensure `.env` is excluded in your VCS if this is intended to be private. If `.env` is already tracked, rotate credentials immediately and remove secrets from history.
- The database name used in queries is `asteriskcdrdb`. Ensure this schema exists on each host.
- For ASR endpoint, the DB should provide a `country_codes` table and a scalar function `get_country_code(number)`. TODO: Document schema and function definition for `country_codes` and `get_country_code`.

## Installation (local)

```bash
python -m venv .venv
.
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# create and fill .env as shown above

# Run dev server (Flask built-in; not for production)
python app.py
```

By default the development server listens on `http://127.0.0.1:5000`.

## Running with Gunicorn (recommended)

```bash
gunicorn --bind 0.0.0.0:8000 app:app
```

## Docker

Build and run the container:

```bash
# Build
docker build -t callstat-app:latest .

# Run (point to a local .env file)
docker run --name callstat \
  --env-file .env \
  -p 8000:8000 \
  callstat-app:latest
```

The container runs `gunicorn --bind 0.0.0.0:8000 app:app` and exposes port 8000.

## API

All endpoints require a path token: `/api/v1/<token>/...`. The token must exactly match `API_TOKEN` from the environment; otherwise the API returns HTTP 401.

Common query parameter for both endpoints:
- `date`: One of `YYYY-MM-DD` (specific date), `week` (previous full work week per query in code), or `month` (previous calendar month). If omitted, defaults to the current date.

### 1) Call statistics per extension

```
GET /api/v1/{token}/callstat?date=YYYY-MM-DD|week|month
```

Response example:

```json
{
  "data": [
    {
      "cnum": "2001",
      "cnam": "John Doe",
      "call_count": 10,
      "total_call_time_minutes": 45.5,
      "long_calls_count": 3,
      "total_long_calls_minutes": 12.5,
      "unique_calls": 5
    }
  ],
  "date": "2025-12-02",
  "errors": { "db-host": "error message" }
}
```

Notes
- Results combine data across the configured databases. If any DB fails, an `errors` object is included while still returning available data from others.
- The SQL excludes 4-digit internal calls and focuses on `lastapp IN ('Dial','Busy','Congestion')` with non-failed dispositions.

### 2) ASR by destination country code

```
GET /api/v1/{token}/asrstat?date=YYYY-MM-DD|week|month
```

Response example (per database):

```json
{
  "date": "2025-12-02",
  "databases": {
    "db1.example.com": {
      "status": "success",
      "data": [
        {
          "country_code": "+1",
          "country": "United States",
          "answered_calls": 120,
          "total_calls": 200,
          "asr_percentage": 60.0,
          "unique_destinations": 85,
          "total_talk_minutes": 430.5
        }
      ]
    }
  }
}
```

Notes
- Requires DB-side function `get_country_code(cdr.dst)` and table `asteriskcdrdb.country_codes` with mapping. TODO: Provide DDL and function body.

## Scripts and commands

- Development server: `python app.py`
- Gunicorn (local): `gunicorn --bind 0.0.0.0:8000 app:app`
- Docker build: `docker build -t callstat-app:latest .`
- Docker run: `docker run --env-file .env -p 8000:8000 callstat-app:latest`

## Testing

There are currently no automated tests in this repository. TODOs:
- Add unit tests for SQL assembly and result combining.
- Add endpoint integration tests using Flask test client.
- Provide a sample SQL fixture or a Docker Compose for a local MySQL with mock `asteriskcdrdb`.

## Production deployment (optional)

The following high-level steps can be used to deploy on a Linux server behind Nginx using Supervisor. Adjust paths and usernames as needed.

1) Install system packages

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv default-libmysqlclient-dev nginx supervisor
```

2) Create app directory and venv

```bash
sudo mkdir -p /opt/asterisk-api
sudo chown $USER:$USER /opt/asterisk-api
cd /opt/asterisk-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

3) Run with Supervisor

Create `/etc/supervisor/conf.d/asterisk-api.conf`:

```ini
[program:asterisk-api]
directory=/opt/asterisk-api
command=/opt/asterisk-api/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
autostart=true
autorestart=true
stderr_logfile=/var/log/asterisk-api/error.log
stdout_logfile=/var/log/asterisk-api/access.log
user=www-data
```

Then:

```bash
sudo mkdir -p /var/log/asterisk-api
sudo supervisorctl reread && sudo supervisorctl update && sudo supervisorctl start asterisk-api
```

4) Nginx reverse proxy

```nginx
server {
  listen 80;
  server_name your-server-domain.com;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Optionally secure with Let's Encrypt using certbot. See original guide below for more tips (firewall, monitoring, backups).

## Troubleshooting

- 401 Unauthorized: Ensure path token equals `API_TOKEN`.
- DB errors/timeouts: Check connectivity to each `DBx_HOST` and credentials. The response may include an `errors` section per database.
- Empty results: Confirm that `asteriskcdrdb.cdr` contains data for the requested date range and that internal call filters match your dialing plan.
- ASR endpoint fails: Ensure the `country_codes` table and `get_country_code` function exist. Check DB permissions to execute functions.

## License

Proprietary – All Rights Reserved

This software is not open-source. No one is allowed to use, copy, modify, merge, publish, distribute, sublicense, or sell copies of this software, in whole or in part, without the prior written permission of the owner.

By default, no license or usage rights are granted. To request permission, please contact the repository owner.

See the LICENSE file in this repository for the full terms.

---

### Appendix: Original Ubuntu deployment guide

The repository previously included a detailed step-by-step Ubuntu deployment guide with Supervisor, Nginx, SSL, monitoring, backups, and maintenance commands. Those steps remain generally applicable; review and adapt them to your environment. Ensure that commands reference `app:app` and port `8000` as shown above and that secrets are managed securely (do not keep real credentials in `.env` under version control).