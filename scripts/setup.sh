#!/bin/bash
# =============================================================================
# GPG Webservice Setup Script
# =============================================================================
# Automates the setup process for the GPG Webservice suite
#
# Usage:
#   ./setup.sh          # Interactive mode
#   ./setup.sh --auto   # Automated mode (no prompts)
#
# This script:
#   1. Checks prerequisites (Docker, OpenSSL, etc.)
#   2. Creates .env files from templates
#   3. Generates secure secrets
#   4. Builds Docker images
#   5. Starts all services
#   6. Runs health checks
#   7. Displays access URLs
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
AUTO_MODE=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --auto) AUTO_MODE=true ;;
        --help)
            echo "Usage: $0 [--auto] [--help]"
            echo "  --auto   Run in automated mode (no prompts)"
            echo "  --help   Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    print_success "$1 is installed"
    return 0
}

confirm() {
    if [ "$AUTO_MODE" = true ]; then
        return 0
    fi
    read -p "$1 (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================

print_header "Step 1: Checking Prerequisites"

ALL_GOOD=true

check_command docker || ALL_GOOD=false
check_command docker-compose || {
    # Try docker compose (v2)
    if docker compose version &> /dev/null; then
        print_success "docker compose (v2) is installed"
        alias docker-compose='docker compose'
    else
        ALL_GOOD=false
    fi
}
check_command git || ALL_GOOD=false
check_command openssl || ALL_GOOD=false
check_command curl || ALL_GOOD=false

if [ "$ALL_GOOD" = false ]; then
    print_error "Missing prerequisites. Please install the required tools."
    exit 1
fi

echo ""

# =============================================================================
# Step 2: Check Ports
# =============================================================================

print_header "Step 2: Checking Port Availability"

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        print_warning "Port $1 is already in use"
        return 1
    else
        print_success "Port $1 is available"
        return 0
    fi
}

PORTS_OK=true
check_port $FLASK_PORT || PORTS_OK=false
check_port $MCP_PORT || PORTS_OK=false
check_port $DASHBOARD_PORT || PORTS_OK=false

if [ "$PORTS_OK" = false ]; then
    print_warning "Some ports are in use. You may need to stop conflicting services or change ports in .env"
    if ! confirm "Continue anyway?"; then
        exit 1
    fi
fi

echo ""

# =============================================================================
# Step 3: Create Environment Files
# =============================================================================

print_header "Step 3: Creating Environment Files"

# Root .env
if [ -f .env ]; then
    print_warning "Root .env already exists"
    if confirm "Overwrite root .env?"; then
        cp .env.example .env
        print_success "Root .env created from template"
    else
        print_info "Keeping existing root .env"
    fi
else
    cp .env.example .env
    print_success "Root .env created from template"
fi

# REST API .env
cd gpg-webservice-rest
if [ -f .env ]; then
    print_warning "REST API .env already exists"
    if [ "$AUTO_MODE" = true ]; then
        print_info "Auto mode: keeping existing REST API .env"
    else
        if confirm "Overwrite REST API .env?"; then
            cp .env.example .env
            print_success "REST API .env created from template"
        else
            print_info "Keeping existing REST API .env"
        fi
    fi
else
    cp .env.example .env
    print_success "REST API .env created from template"
fi

echo ""

# =============================================================================
# Step 4: Generate Secrets
# =============================================================================

print_header "Step 4: Generating Secure Secrets"

if [ -x scripts/generate-secrets.sh ]; then
    if [ "$AUTO_MODE" = true ]; then
        # In auto mode, always regenerate
        print_info "Auto mode: Regenerating secrets..."
        yes | ./scripts/generate-secrets.sh
    else
        ./scripts/generate-secrets.sh
    fi
else
    print_error "scripts/generate-secrets.sh not found or not executable"
    print_info "Generating secrets manually..."

    SERVICE_KEY=$(openssl rand -base64 32)
    SECRET_KEY=$(openssl rand -hex 32)

    # Update .env file
    if grep -q "^SERVICE_KEY_PASSPHRASE=" .env; then
        sed -i.bak "s|^SERVICE_KEY_PASSPHRASE=.*|SERVICE_KEY_PASSPHRASE=$SERVICE_KEY|" .env
    else
        echo "SERVICE_KEY_PASSPHRASE=$SERVICE_KEY" >> .env
    fi

    if grep -q "^SECRET_KEY=" .env; then
        sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
    else
        echo "SECRET_KEY=$SECRET_KEY" >> .env
    fi

    rm -f .env.bak
    print_success "Secrets generated manually"
fi

# Also update root .env
cd ..
SERVICE_KEY=$(grep "^SERVICE_KEY_PASSPHRASE=" gpg-webservice-rest/.env | cut -d '=' -f2-)
SECRET_KEY=$(grep "^SECRET_KEY=" gpg-webservice-rest/.env | cut -d '=' -f2-)

if grep -q "^SERVICE_KEY_PASSPHRASE=" .env; then
    sed -i.bak "s|^SERVICE_KEY_PASSPHRASE=.*|SERVICE_KEY_PASSPHRASE=$SERVICE_KEY|" .env
else
    echo "SERVICE_KEY_PASSPHRASE=$SERVICE_KEY" >> .env
fi

if grep -q "^SECRET_KEY=" .env; then
    sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
else
    echo "SECRET_KEY=$SECRET_KEY" >> .env
fi

rm -f .env.bak

echo ""

# =============================================================================
# Step 5: Build Docker Images
# =============================================================================

print_header "Step 5: Building Docker Images"

print_info "This may take a few minutes..."
docker-compose build

print_success "Docker images built"

echo ""

# =============================================================================
# Step 6: Start Services
# =============================================================================

print_header "Step 6: Starting Services"

docker-compose up -d

print_success "Services started"

echo ""

# =============================================================================
# Step 7: Health Checks
# =============================================================================

print_header "Step 7: Running Health Checks"

print_info "Waiting for services to be ready (this may take 30-60 seconds)..."

# Wait for REST API
for i in {1..30}; do
    if curl -sf http://localhost:$FLASK_PORT/openai/function_definitions > /dev/null 2>&1; then
        print_success "REST API is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "REST API failed to start"
        print_info "Check logs: docker-compose logs gpg-webservice"
        exit 1
    fi
    sleep 2
done

# Wait for MCP Server
for i in {1..20}; do
    if curl -sf http://localhost:$MCP_PORT/health > /dev/null 2>&1; then
        print_success "MCP Server is healthy"
        break
    fi
    if [ $i -eq 20 ]; then
        print_warning "MCP Server may not be fully ready"
    fi
    sleep 2
done

# Wait for Dashboard
for i in {1..10}; do
    if curl -sf http://localhost:$DASHBOARD_PORT/health > /dev/null 2>&1; then
        print_success "Dashboard is healthy"
        break
    fi
    if [ $i -eq 10 ]; then
        print_warning "Dashboard may not be fully ready"
    fi
    sleep 2
done

echo ""

# =============================================================================
# Step 8: Create Administrator Account
# =============================================================================

print_header "Step 8: Creating Administrator Account"

if [ "$AUTO_MODE" = true ]; then
    print_info "Auto mode: Skipping administrator account creation"
    print_info "Set ADMIN_USERNAMES in .env and register manually"
else
    if confirm "Would you like to create an administrator account?"; then
        echo ""
        read -p "Admin username (default: administrator): " ADMIN_USER
        ADMIN_USER=${ADMIN_USER:-administrator}
        
        read -s -p "Admin password (must be strong): " ADMIN_PASS
        echo ""
        
        if [ -z "$ADMIN_PASS" ]; then
            print_error "Password cannot be empty"
        else
            # Add admin username to .env
            if grep -q "^ADMIN_USERNAMES=" .env; then
                # Append to existing
                CURRENT=$(grep "^ADMIN_USERNAMES=" .env | cut -d '=' -f2-)
                if [ -z "$CURRENT" ]; then
                    sed -i.bak "s|^ADMIN_USERNAMES=.*|ADMIN_USERNAMES=$ADMIN_USER|" .env
                else
                    sed -i.bak "s|^ADMIN_USERNAMES=.*|ADMIN_USERNAMES=$CURRENT,$ADMIN_USER|" .env
                fi
            else
                echo "ADMIN_USERNAMES=$ADMIN_USER" >> .env
            fi
            rm -f .env.bak
            
            # Restart REST API to pick up new env var
            print_info "Restarting REST API with admin configuration..."
            docker-compose restart gpg-webservice-rest
            
            # Wait for service
            sleep 5
            
            # Try to register admin user
            print_info "Registering administrator account..."
            REGISTER_RESULT=$(curl -s -X POST http://localhost:5555/register \
                -H "Content-Type: application/json" \
                -d "{\"username\": \"$ADMIN_USER\", \"password\": \"$ADMIN_PASS\"}" 2>&1)
            
            if echo "$REGISTER_RESULT" | grep -q "successfully"; then
                print_success "Administrator account created: $ADMIN_USER"
                print_info "Save your credentials securely!"
            elif echo "$REGISTER_RESULT" | grep -q "already exists"; then
                print_warning "Username $ADMIN_USER already exists"
                print_info "You can still use it for admin operations if configured in ADMIN_USERNAMES"
            else
                print_warning "Could not auto-register administrator"
                print_info "Register manually at: http://localhost:8080/register.html"
                print_info "Username: $ADMIN_USER"
            fi
            
            print_success "Admin username added to ADMIN_USERNAMES: $ADMIN_USER"
        fi
    else
        print_info "Skipping administrator account creation"
        print_info "To enable admin access later, set ADMIN_USERNAMES in .env"
    fi
fi

echo ""

# =============================================================================
# Step 9: Display Access Information
# =============================================================================

print_header "✅ Setup Complete!"

echo "Your GPG Webservice suite is now running!"
echo ""
echo "Access URLs:"
echo "  🌐 REST API:    http://localhost:$FLASK_PORT"
echo "  🤖 MCP Server:  http://localhost:$MCP_PORT"
echo "  📊 Dashboard:   http://localhost:$DASHBOARD_PORT"
echo ""
echo "Quick Test:"
echo "  curl http://localhost:$FLASK_PORT/openai/function_definitions"
echo ""
echo "Next Steps:"
echo "  1. Open dashboard: http://localhost:$DASHBOARD_PORT/"
if grep -q "^ADMIN_USERNAMES=" .env && [ -n "$(grep "^ADMIN_USERNAMES=" .env | cut -d '=' -f2-)" ]; then
    ADMIN_USER=$(grep "^ADMIN_USERNAMES=" .env | cut -d '=' -f2- | cut -d ',' -f1)
    echo "  2. Login with admin account: $ADMIN_USER"
    echo "  3. Access admin panel: http://localhost:$DASHBOARD_PORT/admin.html"
else
    echo "  2. Register a user"
    echo "  3. Try signing a file"
fi
echo ""
echo "Documentation:"
echo "  📖 README.md       - Complete guide"
echo "  🚀 QUICKSTART.md   - Step-by-step tutorial"
echo "  📚 ./gpg-webservice-rest/docs/ - Full documentation"
echo ""
echo "Useful Commands:"
echo "  docker-compose ps              # Check service status"
echo "  docker-compose logs -f         # View logs"
echo "  docker-compose down            # Stop services"
echo "  docker-compose restart         # Restart services"
echo ""

print_success "Setup completed successfully!"
