# GPG Webservice Dashboard

Web frontend for the GPG Webservice REST API. Provides a user-friendly interface for account management and PGP key operations.

## Features

- **User Registration** - Create an account with automatic GPG keypair generation
- **Login & Authentication** - Secure session management with API key storage
- **Profile Management** - View and update account information
- **PGP Key Operations**:
  - Download public/private keys
  - Upload existing keys
  - View key status
- **API Key Management** - View masked API key, retrieve with password

## Architecture

This is a static web application served by nginx that communicates with the GPG Webservice backend via REST API.

### Components

- **HTML Pages**:
  - `index.html` - Landing page
  - `register.html` - User registration form
  - `login.html` - Login form
  - `profile.html` - User dashboard and profile management

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
3. Optionally upload existing PGP keys
4. Submit form
5. **Important**: Copy and save the API key (shown once only!)
6. Continue to login

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
5. View/copy API key

## Security

- API keys stored in `sessionStorage` (cleared on tab close)
- Password confirmation required for sensitive operations
- HTTPS recommended for production
- CSP headers configured in nginx
- All API communication uses secure headers

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
- `POST /login` - User authentication
- `POST /get_api_key` - Retrieve masked API key
- `GET /profile` - Get user profile
- `PUT /profile` - Update user profile
- `GET /keys/download?type=public|private` - Download PGP keys
- `POST /keys/upload` - Upload PGP keys

All protected endpoints require `X-API-KEY` header.

## Troubleshooting

### Cannot connect to backend

- Check backend is running: `curl http://localhost:5555/openai/function_definitions`
- Verify CORS configuration in backend allows dashboard origin
- Check browser console for errors

### API key not working

- Ensure API key was copied correctly during registration
- Check `sessionStorage` in browser DevTools
- Verify API key hasn't been revoked

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
