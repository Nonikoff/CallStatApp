# Asterisk Call Statistics API

This API provides call statistics from an Asterisk CDR database.

## Setup

1. Install the required packages:

`pip install -r requirements`

2. Create a `.env` file with your database credentials and API token.

3. Run the application:
   

`   gunicorn app:app`


## API Endpoints

### Get Call Statistics


GET /api/v1/{token}/callstat?date=YYYY-MM-DD


Parameters:
- `token`: Your API authentication token
- `date`: (Optional) The date for which to retrieve statistics (default: current date)

Response:
`json
[
  {
    "src": "1234",
    "cnam": "John Doe",
    "unique_calls": 5,
    "call_count": 10,
    "formatted_total_time_minutes": 45.5
  },
  ...
]`

## 1. Prepare Your Server

### Install Required System Packages

```bash
# Update package lists
sudo apt update

# Install Python and related tools
sudo apt install python3 python3-pip python3-venv

# Install MySQL client (for database connections)
sudo apt install default-libmysqlclient-dev

# Install Nginx (for reverse proxy)
sudo apt install nginx

# Install Supervisor (for process management)
sudo apt install supervisor
```

## 2. Set Up Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/asterisk-api

# Set ownership (replace 'yourusername' with your actual username)
sudo chown yourusername:yourusername /opt/asterisk-api

# Navigate to the directory
cd /opt/asterisk-api
```

## 3. Create a Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

## 4. Deploy Application Files

Copy application files to the server:

Copy or clone App git to dir

## 5. Install Python Dependencies

```bash
# Make sure you're in the application directory with activated virtual environment
pip install -r requirements.txt

# Install Gunicorn (WSGI server)
pip install gunicorn
```

## 6. Test Application

```bash
# Test the application with Gunicorn
gunicorn --bind 127.0.0.1:8000 app:app
```

Try accessing API in another terminal:
```bash
curl "http://127.0.0.1:8000/api/v1/your_token/callstat?date=2025-06-05"
```

Press Ctrl+C to stop Gunicorn after testing.

## 7. Configure Supervisor

Create a supervisor configuration file:

```bash
sudo nano /etc/supervisor/conf.d/asterisk-api.conf
```

Add the following content:

```ini
[program:asterisk-api]
directory=/opt/asterisk-api
command=/opt/asterisk-api/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
autostart=true
autorestart=true
stderr_logfile=/var/log/asterisk-api/error.log
stdout_logfile=/var/log/asterisk-api/access.log
user=yourusername
```

Create log directories:

```bash
sudo mkdir -p /var/log/asterisk-api
sudo chown yourusername:yourusername /var/log/asterisk-api
```

Update and start supervisor:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start asterisk-api
```

## 8. Configure Nginx as a Reverse Proxy

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/asterisk-api
```

Add the following content:

```nginx
server {
    listen 80;
    server_name your-server-domain.com;  # Replace with your domain or IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/asterisk-api /etc/nginx/sites-enabled/
sudo nginx -t  # Test the configuration
sudo systemctl restart nginx
```

## 9. Set Up SSL with Let's Encrypt (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx
```

Obtain and install SSL certificate
```bash
sudo certbot --nginx -d your-server-domain.com
```

## 10. Secure Application

### Firewall Configuration

```bash
Allow SSH, HTTP, and HTTPS
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### Secure the .env File

```bash
#Ensure proper permissions for .env

chmod 600 /opt/asterisk-api/.env
```

## 11. Set Up Monitoring (Optional)

Consider setting up monitoring for your application:

```bash
#Install monitoring tools (example: netdata)

sudo apt install netdata

#Enable and start the service

sudo systemctl enable netdata
sudo systemctl start netdata
```
## 12. Test Production Deployment

Test your API with curl or a web browser:

```bash
curl "https://your-server-domain.com/api/v1/your_token/callstat?date=2025-06-05"
```

## 13. Set Up Regular Backups (Optional)

Create a backup script:

```bash
sudo nano /opt/backup-asterisk-api.sh
```

Add the following content:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/asterisk-api"
mkdir -p $BACKUP_DIR
cp -r /opt/asterisk-api $BACKUP_DIR/asterisk-api-$(date +%Y%m%d)
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} \;
```
Make it executable and add to crontab:

```bash
sudo chmod +x /opt/backup-asterisk-api.sh
sudo crontab -e
```

Add this line to run backups daily:

0 2 * * * /opt/backup-asterisk-api.sh

## 14. Maintenance Tasks

### Updating Application

```bash
#Navigate to your application directory

cd /opt/asterisk-api

#Activate virtual environment

source venv/bin/activate

#Pull latest code (if using git)

git pull

#Install any new dependencies

pip install -r requirements.txt

#Restart the application

sudo supervisorctl restart asterisk-api
```
### Checking Logs

```bash
#Application logs

sudo tail -f /var/log/asterisk-api/access.log
sudo tail -f /var/log/asterisk-api/error.log

#Nginx logs

sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```
## 15. Troubleshooting

If you encounter issues:

1. Check application logs: `/var/log/asterisk-api/error.log`

2. Check Nginx logs: `/var/log/nginx/error.log`

3. Check supervisor status: `sudo supervisorctl status asterisk-api`

4. Test the application directly: `curl http://127.0.0.1:8000/api/v1/your_token/callstat?date=2025-06-05`

This comprehensive guide should help you deploy your Flask API to production with proper security, monitoring, and maintenance procedures. Let me know if you need any clarification on any of these steps!