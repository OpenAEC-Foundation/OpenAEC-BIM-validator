#!/bin/bash
# Deploy script for OpenAEC BIM Validator
# Usage: ./deploy.sh [domain]
# Example: ./deploy.sh bim.3bm.nl

set -e

DOMAIN="${1:-localhost}"
REPO_URL="https://github.com/OpenAEC-Foundation/OpenAEC-BIM-validator.git"
APP_DIR="/opt/bim-validator"

echo "=== OpenAEC BIM Validator Deploy ==="
echo "Domain: $DOMAIN"

# Clone or pull
if [ -d "$APP_DIR" ]; then
    echo "Updating existing installation..."
    cd "$APP_DIR"
    git pull origin master
else
    echo "Fresh install..."
    sudo mkdir -p "$APP_DIR"
    sudo chown "$USER:$USER" "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# Build and start
echo "Building Docker image..."
docker compose build

echo "Starting containers..."
docker compose up -d

echo ""
echo "=== Deploy complete ==="
echo "App running on http://127.0.0.1:8000"
echo ""
echo "Add this to your Caddyfile to expose it:"
echo ""
echo "  $DOMAIN {"
echo "      reverse_proxy 127.0.0.1:8000"
echo "  }"
echo ""
echo "Then reload Caddy: sudo systemctl reload caddy"
