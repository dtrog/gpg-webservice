# Render.com Deployment Guide

## Quick Start

### 1. Deploy to Render

1. Push code to GitHub (including `render.yaml`)
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click **"New"** → **"Blueprint"**
4. Connect your GitHub repository
5. Render detects `render.yaml` and shows 3 services:
   - `gpg-webservice-rest` (Flask API)
   - `gpg-webservice-mcp` (MCP Server)
   - `gpg-webservice-dashboard` (Web UI)
6. Click **"Apply"** to create all services

### 2. Configure Secrets (REQUIRED)

After deployment, services will fail until you set required secrets. Go to each service in the Render dashboard and add these environment variables:

#### For `gpg-webservice-rest` (REST API)

**Generate secrets locally:**
```bash
# Generate SERVICE_KEY_PASSPHRASE
openssl rand -base64 32

# Generate SECRET_KEY
openssl rand -hex 32
```

**Add in Render Dashboard:**
1. Go to `gpg-webservice-rest` service
2. Click **"Environment"** tab
3. Add these variables:

| Variable | Example Value | How to Generate |
|----------|---------------|-----------------|
| `SERVICE_KEY_PASSPHRASE` | `hHfabDCTsLWy...` | `openssl rand -base64 32` |
| `SECRET_KEY` | `a796f0818f23...` | `openssl rand -hex 32` |
| `ADMIN_USERNAMES` | `administrator,alice` | Comma-separated list |
| `ADMIN_GPG_KEYS` | See below | JSON with GPG public keys |

**ADMIN_GPG_KEYS format:**
```json
{
  "administrator": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n<your-key-here>\n-----END PGP PUBLIC KEY BLOCK-----\n",
  "alice": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n<alice-key-here>\n-----END PGP PUBLIC KEY BLOCK-----\n"
}
```

**Important:** 
- Use literal `\n` in the JSON string (not actual newlines)
- The JSON must be a single line
- Test locally first by setting in `.env` file

#### For `gpg-webservice-mcp` (MCP Server)

1. Go to `gpg-webservice-mcp` service
2. Click **"Environment"** tab
3. Add:

| Variable | Value |
|----------|-------|
| `GPG_API_BASE` | `https://gpg-webservice-rest.onrender.com` |
| `GPG_API_KEY` | (Optional) API key for requests |

**Note:** Replace with your actual REST service URL from Render dashboard.

#### For `gpg-webservice-dashboard` (Dashboard)

1. Go to `gpg-webservice-dashboard` service
2. Click **"Environment"** tab
3. Add:

| Variable | Value |
|----------|-------|
| `API_URL` | `https://gpg-webservice-rest.onrender.com` |

### 3. Restart Services

After adding environment variables:
1. Go to each service
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Wait for builds to complete (~2-5 minutes each)

### 4. Verify Deployment

Test each service:

```bash
# REST API
curl https://gpg-webservice-rest.onrender.com/

# MCP Server
curl https://gpg-webservice-mcp.onrender.com/health

# Dashboard
curl https://gpg-webservice-dashboard.onrender.com/
```

## Service URLs

After deployment, your services will be available at:
- **REST API:** `https://gpg-webservice-rest.onrender.com`
- **MCP Server:** `https://gpg-webservice-mcp.onrender.com`
- **Dashboard:** `https://gpg-webservice-dashboard.onrender.com`

## Updating Environment Variables

To update secrets after initial deployment:

1. Go to Render Dashboard
2. Select the service (e.g., `gpg-webservice-rest`)
3. Click **"Environment"** tab
4. Click **"Add Environment Variable"** or edit existing ones
5. Click **"Save Changes"**
6. Render automatically redeploys the service

## Admin GPG Keys Setup

### Option 1: Generate a New GPG Key

```bash
# Generate a new GPG key
gpg --full-generate-key

# Export public key
gpg --armor --export your-email@example.com > admin_key.pub

# View key (copy this)
cat admin_key.pub
```

### Option 2: Use Existing GPG Key

```bash
# List your GPG keys
gpg --list-keys

# Export public key for existing key
gpg --armor --export KEY_ID > admin_key.pub
```

### Format for Render

Convert the key to JSON format:
```bash
# Show key with literal \n
cat admin_key.pub | sed 's/$/\\n/' | tr -d '\n'
```

Then wrap in JSON:
```json
{"administrator":"-----BEGIN PGP PUBLIC KEY BLOCK-----\\n\\nmQINBG...\\n-----END PGP PUBLIC KEY BLOCK-----\\n"}
```

Paste this entire JSON string into Render's `ADMIN_GPG_KEYS` environment variable.

## Database Options

### SQLite (Default - Free Tier)

- Stored on persistent disk (1 GB)
- Automatic backups via Render
- Good for development/testing
- Limited to single instance

### PostgreSQL (Recommended for Production)

1. In Render Dashboard, click **"New"** → **"PostgreSQL"**
2. Create database
3. Copy the **Internal Database URL**
4. Update `gpg-webservice-rest` environment:
   - Set `DATABASE_URL` to the PostgreSQL connection string
5. Restart the REST service

## TLS/HTTPS

- **Render handles TLS automatically** at the edge
- Services detect `RENDER` environment variable and run HTTP internally
- No certificate management needed
- Free automatic SSL/TLS for all services

## Monitoring

View logs for each service:
1. Go to service in Render Dashboard
2. Click **"Logs"** tab
3. Monitor real-time logs

## Troubleshooting

### Service fails to start

**Check logs:**
1. Go to service in Render Dashboard
2. Click **"Logs"**
3. Look for error messages

**Common issues:**
- Missing environment variables (especially `SERVICE_KEY_PASSPHRASE`, `SECRET_KEY`)
- Invalid JSON in `ADMIN_GPG_KEYS`
- Wrong `GPG_API_BASE` URL for MCP service

### MCP can't connect to REST API

1. Verify REST service is running and healthy
2. Check `GPG_API_BASE` in MCP service matches REST service URL
3. Ensure URL uses `https://` (not `http://`)

### Dashboard shows connection errors

1. Verify `API_URL` is set correctly in dashboard service
2. Check REST API is accessible
3. Open browser console for detailed errors

## Cost Optimization

**Free Tier (Good for development):**
- All three services can run on free tier
- Services sleep after 15 minutes of inactivity
- First request after sleep takes ~30 seconds

**Paid Tier (Production):**
- Upgrade REST API to Starter plan ($7/month) - no sleep
- Keep MCP and Dashboard on free tier (low usage)
- Add PostgreSQL database ($7/month)

## Security Best Practices

1. **Never commit secrets to GitHub**
   - Use Render environment variables
   - Keep `.env` in `.gitignore`

2. **Rotate secrets regularly**
   - Generate new `SERVICE_KEY_PASSPHRASE` and `SECRET_KEY`
   - Update in Render Dashboard
   - Restart services

3. **Use PostgreSQL in production**
   - Better performance and reliability
   - Automatic backups
   - Supports multiple connections

4. **Monitor logs**
   - Check for failed authentication attempts
   - Watch for unusual API usage
   - Set up alerts in Render

## Updating Your Deployment

To deploy code changes:

1. Push changes to GitHub:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

2. Render automatically deploys when you push to `main` branch

To update `render.yaml`:
1. Edit `render.yaml` locally
2. Push to GitHub
3. Go to Render Dashboard → Blueprint
4. Click **"Sync"** to apply changes

## Support

- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com/)
- [GPG Webservice GitHub Issues](https://github.com/dtrog/gpg-webservice/issues)
