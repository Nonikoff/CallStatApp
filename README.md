# Asterisk Call Statistics API (CallStatApp)

A small Flask API that aggregates call statistics from one or more Asterisk CDR MySQL databases. It exposes endpoints to get per-extension call time summaries and Answer-Seizure Ratio (ASR) by destination country code.

Updated: 2025-12-05

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

There are two ways to run with Docker:

1) Quick single-container run (no reverse proxy)
2) Full setup with Nginx (HTTP or HTTPS with automatic Let's Encrypt) using the provided `install-docker.sh` script

### Option A — Quick single-container run

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

### Option B — Automated setup with Nginx (HTTP or HTTPS)

Use the provided Bash script `install-docker.sh` to generate a production-ready Docker Compose configuration with Nginx in front of the app. The script supports:
- HTTP only (port 80)
- HTTPS with automatic SSL via Let's Encrypt (ports 80/443) and background renewal using a Certbot container

Prerequisites
- Linux host with Bash (the script is a Bash script)
- Docker and Docker Compose installed
  - Docker: https://docs.docker.com/get-docker/
  - Docker Compose (classic): https://docs.docker.com/compose/install/
- Open firewall for ports 80 (HTTP) and 443 (HTTPS) as needed

Steps
```bash
# 1) Make sure your .env exists (see Environment Variables section)
#    If you don't have it yet, the script can scaffold a template for you.

# 2) Run the installer from the project root
chmod +x install-docker.sh

# HTTP only (default)
./install-docker.sh http

# or HTTPS (you will be prompted for domain and email)
./install-docker.sh https

# 3) Start services (script creates helper scripts)
./start.sh

# 4) See status/logs
./logs.sh

# 5) Stop services
./stop.sh

# (HTTPS only) Manually trigger renewal check if needed
./renew-cert.sh
```

What the installer does
- Creates `.env` if missing (with placeholder values — update them!)
- Creates an isolated Docker network
- Writes Nginx configs under `./nginx/`
- Generates `docker-compose.yml` with two (HTTP) or three (HTTPS) services:
  - `callstat` (this app, bound to 127.0.0.1:8000 inside Compose)
  - `nginx` (fronts the app; publishes 80 and optionally 443)
  - `certbot` (HTTPS only; renews certificates automatically)
- Creates helper scripts: `start.sh`, `stop.sh`, `logs.sh`, and `renew-cert.sh` (HTTPS)

Access URLs
- HTTP mode: `http://localhost/` (port 80 exposed)
- HTTPS mode: `https://your-domain/` with HTTP redirected to HTTPS
- Health checks: `/health`

Notes
- DNS: For HTTPS, point your domain (and `www`) to this server and allow inbound 80/443 before running `./start.sh` so Certbot can validate.
- Renewal: The `certbot` container runs a renewal loop. Keep it running (i.e., don’t stop Compose) for auto-renewal.
- docker-compose vs docker compose: The scripts use `docker-compose` (classic). If your system only has the plugin `docker compose`, create an alias or install the classic binary.
- The generated Compose maps the application container port `8000` to `127.0.0.1:${APP_PORT}` and publishes ports via Nginx (`80` and optionally `443`).

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
- Requires DB-side function `get_country_code(cdr.dst)` and table `asteriskcdrdb.country_codes` with mapping.
```sql
-- ASR % by country START
CREATE TABLE country_codes (
    code VARCHAR(10) PRIMARY KEY,
    country VARCHAR(100) NOT NULL
);
INSERT INTO country_codes (code, country) VALUES
('1', 'United States/Canada'),
('7', 'Russia/Kazakhstan'),
('20', 'Egypt'),
('27', 'South Africa'),
('30', 'Greece'),
('31', 'Netherlands'),
('32', 'Belgium'),
('33', 'France'),
('34', 'Spain'),
('36', 'Hungary'),
('39', 'Italy'),
('40', 'Romania'),
('41', 'Switzerland'),
('43', 'Austria'),
('44', 'United Kingdom'),
('45', 'Denmark'),
('46', 'Sweden'),
('47', 'Norway'),
('48', 'Poland'),
('49', 'Germany'),
('51', 'Peru'),
('52', 'Mexico'),
('53', 'Cuba'),
('54', 'Argentina'),
('55', 'Brazil'),
('56', 'Chile'),
('57', 'Colombia'),
('58', 'Venezuela'),
('60', 'Malaysia'),
('61', 'Australia'),
('62', 'Indonesia'),
('63', 'Philippines'),
('64', 'New Zealand'),
('65', 'Singapore'),
('66', 'Thailand'),
('81', 'Japan'),
('82', 'South Korea'),
('84', 'Vietnam'),
('86', 'China'),
('90', 'Turkey'),
('91', 'India'),
('92', 'Pakistan'),
('93', 'Afghanistan'),
('94', 'Sri Lanka'),
('95', 'Myanmar'),
('98', 'Iran'),
('212', 'Morocco'),
('213', 'Algeria'),
('216', 'Tunisia'),
('218', 'Libya'),
('220', 'Gambia'),
('221', 'Senegal'),
('222', 'Mauritania'),
('223', 'Mali'),
('224', 'Guinea'),
('225', 'Ivory Coast'),
('226', 'Burkina Faso'),
('227', 'Niger'),
('228', 'Togo'),
('229', 'Benin'),
('230', 'Mauritius'),
('231', 'Liberia'),
('232', 'Sierra Leone'),
('233', 'Ghana'),
('234', 'Nigeria'),
('235', 'Chad'),
('236', 'Central African Republic'),
('237', 'Cameroon'),
('238', 'Cape Verde'),
('240', 'Equatorial Guinea'),
('241', 'Gabon'),
('242', 'Congo'),
('243', 'Democratic Republic of the Congo'),
('244', 'Angola'),
('245', 'Guinea-Bissau'),
('249', 'Sudan'),
('251', 'Ethiopia'),
('252', 'Somalia'),
('253', 'Djibouti'),
('254', 'Kenya'),
('255', 'Tanzania'),
('256', 'Uganda'),
('257', 'Burundi'),
('258', 'Mozambique'),
('260', 'Zambia'),
('261', 'Madagascar'),
('262', 'Reunion'),
('263', 'Zimbabwe'),
('264', 'Namibia'),
('265', 'Malawi'),
('266', 'Lesotho'),
('267', 'Botswana'),
('268', 'Swaziland'),
('269', 'Comoros'),
('351', 'Portugal'),
('352', 'Luxembourg'),
('353', 'Ireland'),
('354', 'Iceland'),
('355', 'Albania'),
('356', 'Malta'),
('357', 'Cyprus'),
('358', 'Finland'),
('359', 'Bulgaria'),
('370', 'Lithuania'),
('371', 'Latvia'),
('372', 'Estonia'),
('373', 'Moldova'),
('374', 'Armenia'),
('375', 'Belarus'),
('376', 'Andorra'),
('377', 'Monaco'),
('378', 'San Marino'),
('380', 'Ukraine'),
('381', 'Serbia'),
('382', 'Montenegro'),
('385', 'Croatia'),
('386', 'Slovenia'),
('387', 'Bosnia and Herzegovina'),
('389', 'North Macedonia'),
('420', 'Czech Republic'),
('421', 'Slovakia'),
('423', 'Liechtenstein'),
('500', 'Falkland Islands'),
('501', 'Belize'),
('502', 'Guatemala'),
('503', 'El Salvador'),
('504', 'Honduras'),
('505', 'Nicaragua'),
('506', 'Costa Rica'),
('507', 'Panama'),
('509', 'Haiti'),
('591', 'Bolivia'),
('592', 'Guyana'),
('593', 'Ecuador'),
('595', 'Paraguay'),
('598', 'Uruguay'),
('599', 'Netherlands Antilles'),
('670', 'East Timor'),
('672', 'Australian External Territories'),
('673', 'Brunei'),
('674', 'Nauru'),
('675', 'Papua New Guinea'),
('676', 'Tonga'),
('677', 'Solomon Islands'),
('678', 'Vanuatu'),
('679', 'Fiji'),
('680', 'Palau'),
('681', 'Wallis and Futuna'),
('682', 'Cook Islands'),
('683', 'Niue'),
('685', 'Samoa'),
('686', 'Kiribati'),
('687', 'New Caledonia'),
('688', 'Tuvalu'),
('689', 'French Polynesia'),
('690', 'Tokelau'),
('691', 'Micronesia'),
('692', 'Marshall Islands'),
('850', 'North Korea'),
('852', 'Hong Kong'),
('853', 'Macau'),
('855', 'Cambodia'),
('856', 'Laos'),
('880', 'Bangladesh'),
('886', 'Taiwan'),
('960', 'Maldives'),
('961', 'Lebanon'),
('962', 'Jordan'),
('963', 'Syria'),
('964', 'Iraq'),
('965', 'Kuwait'),
('966', 'Saudi Arabia'),
('967', 'Yemen'),
('968', 'Oman'),
('970', 'Palestine'),
('971', 'United Arab Emirates'),
('972', 'Israel'),
('973', 'Bahrain'),
('974', 'Qatar'),
('975', 'Bhutan'),
('976', 'Mongolia'),
('977', 'Nepal'),
('992', 'Tajikistan'),
('993', 'Turkmenistan'),
('994', 'Azerbaijan'),
('995', 'Georgia'),
('996', 'Kyrgyzstan'),
('998', 'Uzbekistan');

-- This is Function to get country code from phone number
DELIMITER //

CREATE FUNCTION get_country_code(phone_number VARCHAR(50))
RETURNS VARCHAR(10)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE country_code VARCHAR(10);
    DECLARE clean_number VARCHAR(50);

    -- Remove leading + if it exists
    IF LEFT(phone_number, 1) = '+' THEN
        SET clean_number = SUBSTRING(phone_number, 2);
    ELSE
        SET clean_number = phone_number;
    END IF;

    -- Find the matching country code (prioritizing longer codes)
    SELECT code INTO country_code
    FROM country_codes
    WHERE clean_number LIKE CONCAT(code, '%')
    ORDER BY LENGTH(code) DESC
    LIMIT 1;

    RETURN country_code;
END //
-- TEST run
SELECT get_country_code('4452325315645') AS country_code;  -- Should return '44'
DELIMITER ;
```

## Scripts and commands

- Development server: `python app.py`
- Gunicorn (local): `gunicorn --bind 0.0.0.0:8000 app:app`
- Docker build: `docker build -t callstat-app:latest .`
- Docker run: `docker run --env-file .env -p 8000:8000 callstat-app:latest`
- Installer (HTTP): `./install-docker.sh http && ./start.sh`
- Installer (HTTPS): `./install-docker.sh https && ./start.sh`
- Show logs (Compose): `./logs.sh`
- Stop services (Compose): `./stop.sh`
- Renew SSL (HTTPS): `./renew-cert.sh`

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
- Docker install script not found: Ensure you’re in the project root and the file is executable (`chmod +x install-docker.sh`).
- HTTPS certificate issuance fails: Verify that your domain resolves to the server’s public IP and that ports 80/443 are open. Re-run `./start.sh` after DNS propagates.
- Only have `docker compose` but script expects `docker-compose`: Install classic Docker Compose or create an alias (`alias docker-compose='docker compose'`).
- Port conflicts: Make sure nothing else is listening on ports 80/443 when starting Nginx.

## License

Personal, Non‑Commercial use only — CC BY‑NC 4.0

This project is licensed under the Creative Commons Attribution‑NonCommercial 4.0 International license (CC BY‑NC 4.0). You may use, copy, and adapt the work for personal, non‑commercial purposes with attribution. Commercial use is not permitted under this license.

- Full legal text: https://creativecommons.org/licenses/by-nc/4.0/legalcode.en
- For commercial licensing or any use beyond the NonCommercial terms, contact: neat.list5884@fastmail.com

See the LICENSE file for the complete license terms.

## Donations

If this project helps you, consider supporting its development:

- Now Payments:

<a href="https://nowpayments.io/donation?api_key=a1bb5801-1614-440d-a0eb-bc8e4f56faf4" target="_blank" rel="noreferrer noopener">
<img src="https://nowpayments.io/images/embeds/donation-button-white.svg" alt="Cryptocurrency & Bitcoin donation button by NOWPayments">
</a>

- Crypto:
  - USDT TRC20: TNchkEFB1r7xU7Cyo3wYx8qDSiKjSFvSJc

Thank you for your support! (Replace the placeholders above with your actual links/addresses.)

---

### Appendix: Original Ubuntu deployment guide

The repository previously included a detailed step-by-step Ubuntu deployment guide with Supervisor, Nginx, SSL, monitoring, backups, and maintenance commands. Those steps remain generally applicable; review and adapt them to your environment. Ensure that commands reference `app:app` and port `8000` as shown above and that secrets are managed securely (do not keep real credentials in `.env` under version control).