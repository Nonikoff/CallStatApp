#!/bin/bash

# Asterisk Call Statistics API - Docker Installation Script
# Supports both HTTP and HTTPS with automatic SSL setup via Certbot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="callstat-app"
APP_VERSION="latest"
DOCKER_NETWORK="callstat-network"
APP_CONTAINER_NAME="callstat"
NGINX_CONTAINER_NAME="callstat-nginx"
CERTBOT_CONTAINER_NAME="callstat-certbot"
APP_PORT="8000"
NGINX_PORT_HTTP="${NGINX_PORT_HTTP:-80}"
NGINX_PORT_HTTPS="${NGINX_PORT_HTTPS:-443}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default installation type
INSTALL_TYPE="http"

# Functions
print_header() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

show_usage() {
    echo -e "${BLUE}Usage: $0 [TYPE]${NC}\n"
    echo "TYPE options:"
    echo "  http    - Install with HTTP only (port 80) - DEFAULT"
    echo "  https   - Install with HTTPS (requires domain and email setup)"
    echo ""
    echo "Examples:"
    echo "  $0 http"
    echo "  $0 https"
    exit 0
}

# Main setup
print_header "Asterisk Call Statistics API - Docker Setup"

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_usage
fi

# Parse installation type
if [ -n "$1" ]; then
    if [[ "$1" == "http" || "$1" == "https" ]]; then
        INSTALL_TYPE="$1"
    else
        print_error "Invalid installation type: $1"
        show_usage
    fi
fi

print_step "Installation Type: ${INSTALL_TYPE^^}"
echo

# Check prerequisites
print_header "Checking Prerequisites"

print_step "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker found: $(docker --version)"

print_step "Checking Docker Compose installation..."
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi
print_success "Docker Compose found: $(docker-compose --version)"

# HTTPS specific setup
if [ "$INSTALL_TYPE" == "https" ]; then
    print_header "HTTPS Configuration Required"
    
    read -p "Enter your domain name (e.g., api.example.com): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        print_error "Domain name is required for HTTPS setup"
        exit 1
    fi
    print_success "Domain set to: $DOMAIN"
    
    read -p "Enter your email (for Let's Encrypt notifications): " EMAIL
    if [ -z "$EMAIL" ]; then
        print_error "Email is required for Let's Encrypt"
        exit 1
    fi
    print_success "Email set to: $EMAIL"
    
    # Ask for renewal preference
    echo
    read -p "Do you want to enable automatic SSL renewal? (y/n, default: y): " AUTO_RENEW
    AUTO_RENEW="${AUTO_RENEW:-y}"
fi

# Environment setup
print_header "Setting Up Environment"

print_step "Creating .env file..."
if [ -f "${PROJECT_DIR}/.env" ]; then
    print_warning ".env file already exists"
else
    cat > "${PROJECT_DIR}/.env" << 'EOF'
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
EOF
    print_success ".env file created"
    print_warning "IMPORTANT: Edit .env and update with real credentials"
fi
echo

# Docker network
print_step "Creating Docker network..."
if docker network ls | grep -q "^${DOCKER_NETWORK}"; then
    print_warning "Network '${DOCKER_NETWORK}' already exists"
else
    docker network create "${DOCKER_NETWORK}"
    print_success "Network created: ${DOCKER_NETWORK}"
fi
echo

# Nginx configuration setup
print_header "Setting Up Nginx"

NGINX_CONF_DIR="${PROJECT_DIR}/nginx"
mkdir -p "${NGINX_CONF_DIR}"

print_step "Creating nginx.conf..."
cat > "${NGINX_CONF_DIR}/nginx.conf" << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/json;

    # Include server configurations
    include /etc/nginx/conf.d/*.conf;
}
EOF
print_success "nginx.conf created"

# Create appropriate Nginx configuration based on installation type
if [ "$INSTALL_TYPE" == "http" ]; then
    print_step "Creating HTTP configuration..."
    cat > "${NGINX_CONF_DIR}/default.conf" << 'EOF'
upstream callstat_backend {
    server callstat:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name _;
    client_max_body_size 20M;

    location / {
        proxy_pass http://callstat_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_redirect off;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF
    print_success "HTTP configuration created"
else
    print_step "Creating HTTPS configuration..."
    cat > "${NGINX_CONF_DIR}/default.conf" << EOFSSL
upstream callstat_backend {
    server callstat:8000;
    keepalive 32;
}

# HTTP server - redirect to HTTPS
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    client_max_body_size 20M;

    # Allow Let's Encrypt validation
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;
    client_max_body_size 20M;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    location / {
        proxy_pass http://callstat_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_redirect off;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOFSSL
    print_success "HTTPS configuration created"
    
    # Create certbot directories
    mkdir -p "${NGINX_CONF_DIR}/ssl/certs"
    mkdir -p "${NGINX_CONF_DIR}/ssl/renewal"
fi
echo

# Build Docker image
print_header "Building Docker Image"

print_step "Building ${APP_NAME}:${APP_VERSION}..."
if docker build -t "${APP_NAME}:${APP_VERSION}" "${PROJECT_DIR}"; then
    print_success "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    exit 1
fi
echo

# Create docker-compose.yml
print_header "Creating Docker Compose Configuration"

print_step "Generating docker-compose.yml..."

if [ "$INSTALL_TYPE" == "http" ]; then
    cat > "${PROJECT_DIR}/docker-compose.yml" << EOF
version: '3.8'

services:
  callstat:
    image: ${APP_NAME}:${APP_VERSION}
    container_name: ${APP_CONTAINER_NAME}
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    ports:
      - "127.0.0.1:${APP_PORT}:8000"
    networks:
      - ${DOCKER_NETWORK}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    expose:
      - "8000"

  nginx:
    image: nginx:alpine
    container_name: ${NGINX_CONTAINER_NAME}
    ports:
      - "0.0.0.0:${NGINX_PORT_HTTP}:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - callstat
    networks:
      - ${DOCKER_NETWORK}
    restart: unless-stopped

networks:
  ${DOCKER_NETWORK}:
    driver: bridge
EOF
else
    cat > "${PROJECT_DIR}/docker-compose.yml" << EOF
version: '3.8'

services:
  callstat:
    image: ${APP_NAME}:${APP_VERSION}
    container_name: ${APP_CONTAINER_NAME}
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    ports:
      - "127.0.0.1:${APP_PORT}:8000"
    networks:
      - ${DOCKER_NETWORK}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    expose:
      - "8000"

  nginx:
    image: nginx:alpine
    container_name: ${NGINX_CONTAINER_NAME}
    ports:
      - "0.0.0.0:${NGINX_PORT_HTTP}:80"
      - "0.0.0.0:${NGINX_PORT_HTTPS}:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/ssl/certs:/etc/letsencrypt/live/$DOMAIN:ro
      - ./nginx/ssl/renewal:/etc/letsencrypt/renewal:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - callstat
    networks:
      - ${DOCKER_NETWORK}
    restart: unless-stopped

  certbot:
    image: certbot/certbot:latest
    container_name: ${CERTBOT_CONTAINER_NAME}
    volumes:
      - ./nginx/ssl/certs:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    networks:
      - ${DOCKER_NETWORK}
    entrypoint: /bin/sh -c "trap exit TERM; while :; do certbot renew --webroot -w /var/www/certbot --quiet; sleep 12h & wait \$\${!}; done"
    depends_on:
      - nginx
    restart: unless-stopped

networks:
  ${DOCKER_NETWORK}:
    driver: bridge
EOF
fi

print_success "docker-compose.yml created"
echo

# Create start script
print_header "Creating Helper Scripts"

if [ "$INSTALL_TYPE" == "http" ]; then
    cat > "${PROJECT_DIR}/start.sh" << 'EOF'
#!/bin/bash
echo "Starting Asterisk Call Statistics API (HTTP)..."
docker-compose up -d
echo
echo "Services are starting. Waiting for health checks..."
sleep 5
docker-compose ps
echo
echo "✓ API is running at http://localhost:80"
echo "✓ Check health at http://localhost:80/health"
EOF
else
    cat > "${PROJECT_DIR}/start.sh" << EOF
#!/bin/bash
set -e

echo "Starting Asterisk Call Statistics API (HTTPS)..."
echo

# Check if SSL certificates exist
if [ ! -f "nginx/ssl/certs/live/$DOMAIN/fullchain.pem" ]; then
    echo "⚠ SSL certificates not found. Starting Certbot to generate them..."
    echo
    
    # Create necessary directories
    mkdir -p certbot/www
    mkdir -p nginx/ssl/certs
    mkdir -p nginx/ssl/renewal
    
    # Start only nginx and certbot for certificate generation
    docker-compose up -d nginx certbot
    
    echo "Waiting for Nginx to be ready..."
    sleep 5
    
    echo "Generating SSL certificate for $DOMAIN..."
    docker-compose exec certbot certbot certonly \\
        --webroot -w /var/www/certbot \\
        --email $EMAIL \\
        -d $DOMAIN \\
        -d www.$DOMAIN \\
        --agree-tos \\
        --non-interactive \\
        --quiet
    
    if [ \$? -eq 0 ]; then
        echo "✓ SSL certificate generated successfully!"
    else
        echo "✗ Failed to generate SSL certificate"
        exit 1
    fi
    
    echo
fi

# Now start all services
docker-compose up -d

echo "Services are starting. Waiting for health checks..."
sleep 5
docker-compose ps
echo
echo "✓ API is running at https://$DOMAIN"
echo "✓ Check health at https://$DOMAIN/health"
echo "✓ HTTP traffic is automatically redirected to HTTPS"
EOF
fi

chmod +x "${PROJECT_DIR}/start.sh"
print_success "start.sh created"

cat > "${PROJECT_DIR}/stop.sh" << 'EOF'
#!/bin/bash
echo "Stopping all services..."
docker-compose down
echo "✓ All services stopped"
EOF
chmod +x "${PROJECT_DIR}/stop.sh"
print_success "stop.sh created"

cat > "${PROJECT_DIR}/logs.sh" << 'EOF'
#!/bin/bash
echo "Showing Docker Compose logs..."
docker-compose logs -f
EOF
chmod +x "${PROJECT_DIR}/logs.sh"
print_success "logs.sh created"

if [ "$INSTALL_TYPE" == "https" ]; then
    cat > "${PROJECT_DIR}/renew-cert.sh" << EOF
#!/bin/bash
echo "Manually renewing SSL certificate for $DOMAIN..."
docker-compose exec certbot certbot renew --quiet
echo "✓ Certificate renewal check completed"
EOF
    chmod +x "${PROJECT_DIR}/renew-cert.sh"
    print_success "renew-cert.sh created"
fi
echo

# Summary
print_header "Installation Complete ✓"

echo -e "${BLUE}Environment Variables:${NC}"
echo "  Project Directory: ${PROJECT_DIR}"
echo "  Docker Network:    ${DOCKER_NETWORK}"
echo "  App Container:     ${APP_CONTAINER_NAME}"
echo "  Nginx Container:   ${NGINX_CONTAINER_NAME}"
if [ "$INSTALL_TYPE" == "https" ]; then
    echo "  Certbot Container: ${CERTBOT_CONTAINER_NAME}"
    echo "  Domain:            ${DOMAIN}"
    echo "  Email:             ${EMAIL}"
    echo "  Auto Renewal:      ${AUTO_RENEW}"
fi
echo

echo -e "${BLUE}Next Steps:${NC}\n"

echo "1. ${YELLOW}Update environment variables:${NC}"
echo "   Edit .env with your database credentials"
echo "   nano ${PROJECT_DIR}/.env\n"

echo "2. ${YELLOW}Configure DNS (HTTPS only):${NC}"
if [ "$INSTALL_TYPE" == "https" ]; then
    echo "   Point your domain ($DOMAIN) to this server's IP address"
    echo "   Ensure ports 80 and 443 are accessible from the internet\n"
fi

echo "3. ${YELLOW}Start the services:${NC}"
echo "   cd ${PROJECT_DIR}"
if [ "$INSTALL_TYPE" == "http" ]; then
    echo "   ./start.sh"
    echo "   # Or manually:"
    echo "   # docker-compose up -d\n"
else
    echo "   ./start.sh"
    echo "   # Certbot will automatically generate SSL certificate\n"
fi

echo "4. ${YELLOW}Monitor logs:${NC}"
echo "   ./logs.sh\n"

echo "5. ${YELLOW}Stop services:${NC}"
echo "   ./stop.sh\n"

echo -e "${BLUE}Service Access:${NC}"
if [ "$INSTALL_TYPE" == "http" ]; then
    echo "  API URL:  http://localhost:80"
    echo "  Health:   http://localhost:80/health"
else
    echo "  API URL:  https://${DOMAIN}"
    echo "  Health:   https://${DOMAIN}/health"
    echo "  HTTP:     http://${DOMAIN} (redirects to HTTPS)"
fi
echo

echo -e "${BLUE}Useful Commands:${NC}"
echo "  View status:       docker-compose ps"
echo "  View logs:         docker-compose logs -f"
echo "  Restart service:   docker-compose restart"
if [ "$INSTALL_TYPE" == "https" ]; then
    echo "  Renew certificate: ./renew-cert.sh"
fi
echo

echo -e "${YELLOW}⚠ Important Notes:${NC}"
echo "  • Do NOT commit .env with real credentials"
echo "  • Add .env to .gitignore"
echo "  • Rotate database credentials regularly"
if [ "$INSTALL_TYPE" == "https" ]; then
    echo "  • SSL certificate auto-renewal is enabled"
    echo "  • Keep certbot container running for auto-renewal"
    echo "  • Check certificate expiry: docker-compose exec certbot certbot certificates"
fi
echo
