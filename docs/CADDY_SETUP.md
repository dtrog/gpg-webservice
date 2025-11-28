# Caddy Reverse Proxy Setup (Optional)

Caddy provides a single HTTPS entry point with automatic TLS certificates and clean URL routing.

## Why Use Caddy?

**Without Caddy:**
- Services on different ports: `:5555` (REST), `:3000` (MCP), `:8080` (Dashboard)
- Manual TLS certificate management
- Expose multiple ports on firewall

**With Caddy:**
- Single port 443 (HTTPS) with automatic Let's Encrypt certificates
- Clean URLs: `/api/*`, `/mcp/*`, `/` (dashboard)
- Simplified firewall rules

## Installation

```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

## Configuration

Create `/etc/caddy/Caddyfile`:

```caddy
your-domain.com {
    # MCP server on /mcp path
    handle /mcp* {
        reverse_proxy localhost:3000
    }
    
    # REST API endpoints
    handle /api* {
        reverse_proxy localhost:5555
    }
    
    handle /register* {
        reverse_proxy localhost:5555
    }
    
    handle /login* {
        reverse_proxy localhost:5555
    }
    
    handle /profile* {
        reverse_proxy localhost:5555
    }
    
    handle /admin* {
        reverse_proxy localhost:5555
    }
    
    handle /openai* {
        reverse_proxy localhost:5555
    }
    
    handle /swagger* {
        reverse_proxy localhost:5555
    }
    
    handle /static* {
        reverse_proxy localhost:5555
    }
    
    handle /favicon* {
        reverse_proxy localhost:5555
    }
    
    # Dashboard (static files)
    handle /*.html {
        reverse_proxy localhost:8080
    }
    
    handle /css/* {
        reverse_proxy localhost:8080
    }
    
    handle /js/* {
        reverse_proxy localhost:8080
    }
    
    # Default to dashboard
    handle / {
        reverse_proxy localhost:8080
    }
}
```

## Enable and Start

```bash
sudo systemctl enable caddy
sudo systemctl restart caddy
sudo systemctl status caddy
```

## DNS Setup

Point your domain's A record to your server's IP:

```
your-domain.com.  IN  A  YOUR_SERVER_IP
```

Caddy will automatically obtain and renew Let's Encrypt certificates.

## Without Caddy

If you don't want to use Caddy, access services directly:

```bash
# REST API
http://your-server:5555/openai/function_definitions

# MCP Server
http://your-server:3000/health

# Dashboard
http://your-server:8080/
```

For production without Caddy, you'll need to:
1. Set up TLS certificates manually (or use the built-in TLS support)
2. Configure firewall to allow ports 5555, 3000, 8080
3. Update dashboard `API_URL` to point to REST API URL
