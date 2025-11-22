# GPG Webservice Dashboard

Web frontend for the GPG Webservice REST API. Provides a user-friendly interface for account management and PGP key operations.

## Features

- **User Registration** - Create an account with automatic GPG keypair generation
- **Login & Authentication** - Secure session management with deterministic session keys (hourly expiration)
- **Profile Management** - View and update account information
- **Admin Panel** - Manage users and perform administrative tasks
- **PGP Key Operations**:
  - Download public/private keys
  - Upload existing keys
  - View key status
- **API Key Management** - Session keys expire hourly, refresh via login
- **Debug Tools** - Test API and MCP connectivity

## Architecture

This is a static web application served by nginx that communicates with the GPG Webservice backend via REST API.

### Components

- **HTML Pages**:
  - `index.html` - Landing page
  - `register.html` - User registration form
  - `login.html` - Login form
  - `profile.html` - User dashboard and profile management
  - `admin.html` - Admin panel for user management
  - `debug.html` - API and MCP connectivity testing

- **Styling**: `css/styles.css` - Responsive CSS with modern design

- **JavaScript**: `js/app.js` - Shared utilities and API communication

- **Server**: nginx (Alpine Linux) - Serves static files and proxies API requests

## Development

### Local Development

```bash
# Serve with any HTTP server
python3 -m http.server 8080

# Or use live-server
npx live-server --port=8080
```

### Docker Development

```bash
# Build the container
docker build -t gpg-dashboard .

# Run standalone
docker run -p 8080:80 gpg-dashboard

# Run with docker-compose (recommended)
cd ../gpg-webservice
docker-compose up gpg-dashboard
```

## Configuration

The dashboard automatically detects the API endpoint:
- **Development**: `http://localhost:5555` (default Flask port)
- **Production**: Uses same origin as dashboard

To change the backend URL, edit `js/app.js`:

```javascript
const API_BASE = 'https://localhost';
```

## Usage

### Registration Flow

1. Visit `/register.html`
2. Fill in username, email, password
3. **Important**: Avoid reserved usernames: `admin`, `root`, `administrator`, `system`, `test`, `null`, `undefined`
4. Optionally upload existing PGP keys
5. Submit form
6. **Important**: Copy and save the session key (starts with `sk_`, expires hourly!)
7. Continue to login

**Note**: Session keys expire after 1 hour. Use `/login` to get a fresh session key.

### Login Flow

1. Visit `/login.html`
2. Enter username and password
3. Click "Forgot your API key?" to view masked version
4. Redirected to profile page

### Profile Management

1. View account information
2. Update email address
3. Download PGP keys
4. Upload new keys (requires password confirmation)
5. View/copy session key

### Admin Panel

**Access**: `/admin.html`

**⚠️ IMPORTANT: Admin Access Control**

Admin functions require proper authorization. To designate admin users:

1. **Set the `ADMIN_USERNAMES` environment variable** (comma-separated list):
   ```bash
   export ADMIN_USERNAMES="alice,bob,administrator"
   ```

2. **In docker-compose**, add to `.env` file:
   ```bash
   ADMIN_USERNAMES=alice,bob,administrator
   ```

3. **Restart the REST API service**:
   ```bash
   docker compose restart gpg-webservice-rest
   ```

**Without setting `ADMIN_USERNAMES`, admin endpoints will return 403 Forbidden.**

Features:
- **List All Users** - View all registered users (no auth required)
- **Delete User** - Remove individual users (requires admin session key)
- **Bulk Delete** - Delete multiple users at once (requires admin session key)

**Authentication**: Only users listed in `ADMIN_USERNAMES` can perform delete operations.

**Usage**:
1. Register with a username listed in `ADMIN_USERNAMES`
2. Login to get your session key (starts with `sk_`)
3. Navigate to `/admin.html`
4. Use your session key for delete operations

## Security

- Session keys stored in `sessionStorage` (cleared on tab close)
- **Session keys expire after 1 hour** - refresh via login
- Password confirmation required for sensitive operations
- HTTPS required for production (via Caddy reverse proxy)
- CSP headers configured in nginx
- All API communication uses secure headers
- **Reserved usernames**: Cannot use `admin`, `root`, `administrator`, `system`, `test`, `null`, `undefined`

## Deployment

### Production Checklist

1. **Update API endpoint** in `js/app.js`
2. **Enable HTTPS** (required for production)
3. **Update CORS** origins in backend
4. **Set secure headers** in nginx config
5. **Enable rate limiting** (if needed)

### nginx Configuration

The included `nginx.conf`:
- Serves static files
- Proxies `/api/*` to backend
- Enables gzip compression
- Sets security headers
- Configures caching

### Environment Variables

```bash
# Set custom dashboard port
export DASHBOARD_PORT=8080

# Start with docker-compose
docker-compose up gpg-dashboard
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## File Structure

```
gpg-webservice-dashboard/
├── index.html          # Landing page
├── register.html       # Registration form
├── login.html          # Login form
├── profile.html        # User dashboard
├── css/
│   └── styles.css      # Responsive styles
├── js/
│   └── app.js          # Shared utilities
├── nginx.conf          # nginx configuration
├── Dockerfile          # Container definition
└── README.md           # This file
```

## API Integration

The dashboard communicates with these backend endpoints:

- `POST /register/form` - User registration (multipart/form-data)
- `POST /login` - User authentication (returns fresh session key)
- `POST /get_api_key` - Retrieve masked session key
- `GET /profile` - Get user profile
- `PUT /profile` - Update user profile
- `GET /keys/download?type=public|private` - Download PGP keys
- `POST /keys/upload` - Upload PGP keys
- `GET /admin/users` - List all users (admin)
- `DELETE /admin/users/<username>` - Delete user (admin, requires session key)

All protected endpoints require `X-API-KEY` header with session key (starts with `sk_`).

## Troubleshooting

### Cannot connect to backend

- Check backend is running: `curl http://localhost:5555/openai/function_definitions`
- Verify CORS configuration in backend allows dashboard origin
- Check browser console for errors
- Verify Caddy reverse proxy is routing correctly

### Session key not working

- Ensure session key was copied correctly (starts with `sk_`)
- Check `sessionStorage` in browser DevTools
- **Session keys expire after 1 hour** - login again to get a fresh key
- Verify session key format is correct

### File upload fails

- Check file is ASCII-armored PGP key format
- Verify file size is reasonable
- Ensure password is correct for upload

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

Same as parent project (MIT)
