# GPG Webservice API Reference

This document provides detailed information about all API endpoints, including request/response formats, authentication requirements, and example usage.

## Authentication

All cryptographic endpoints require authentication using an API key provided in the request header:

```
X-API-KEY: your_api_key_here
```

API keys are obtained through user registration or login endpoints.

## Base URL

```
http://localhost:5000
```

## Endpoints

### User Management

#### Register User

**`POST /register`**

Creates a new user account with automatic GPG key generation.

**Request:**
```json
{
  "username": "alice",
  "password": "secure_password123",
  "email": "alice@example.com"
}
```

**Response (201 Created):**
```json
{
  "message": "User registered successfully",
  "api_key": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567",
  "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n...\n-----END PGP PUBLIC KEY BLOCK-----"
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Username already exists"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "secure_password123",
    "email": "alice@example.com"
  }'
```

---

#### Login User

**`POST /login`**

Authenticates a user and returns their API key.

**Request:**
```json
{
  "username": "alice",
  "password": "secure_password123"
}
```

**Response (200 OK):**
```json
{
  "message": "Login successful",
  "api_key": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
}
```

**Response (401 Unauthorized):**
```json
{
  "error": "Invalid credentials"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "secure_password123"
  }'
```

---

### Cryptographic Operations

#### Sign File

**`POST /sign`**

Signs a file using the user's private key. Returns a detached signature.

**Authentication Required:** Yes

**Request (multipart/form-data):**
- `file`: The file to sign (binary)

**Response (200 OK):**
- Binary signature file (`.sig`)
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="filename.sig"`

**Response (400 Bad Request):**
```json
{
  "error": "file required"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Private key not found"
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "Signing failed: [error details]"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/sign \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt" \
  -o document.txt.sig
```

---

#### Verify Signature

**`POST /verify`**

Verifies a file signature against a public key.

**Authentication Required:** Yes

**Request (multipart/form-data):**
- `file`: The signature file (binary)
- `pubkey`: The public key file (ASCII-armored)

**Response (200 OK):**
```json
{
  "verified": true
}
```

**Response (200 OK - Invalid Signature):**
```json
{
  "verified": false
}
```

**Response (400 Bad Request):**
```json
{
  "error": "file and pubkey required"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/verify \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt.sig" \
  -F "pubkey=@alice_public_key.asc"
```

---

#### Encrypt File

**`POST /encrypt`**

Encrypts a file for a specific recipient using their public key.

**Authentication Required:** Yes

**Request (multipart/form-data):**
- `file`: The file to encrypt (binary)
- `pubkey`: The recipient's public key file (ASCII-armored)

**Response (200 OK):**
- Binary encrypted file (`.gpg`)
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="filename.gpg"`

**Response (400 Bad Request):**
```json
{
  "error": "file and pubkey required"
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "Encryption failed: [error details]"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/encrypt \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt" \
  -F "pubkey=@bob_public_key.asc" \
  -o document.txt.gpg
```

---

#### Decrypt File

**`POST /decrypt`**

Decrypts a file using the user's private key.

**Authentication Required:** Yes

**Request (multipart/form-data):**
- `file`: The encrypted file (binary)

**Response (200 OK):**
- Binary decrypted file
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename="filename.dec"`

**Response (400 Bad Request):**
```json
{
  "error": "file required"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Private key not found"
}
```

**Response (500 Internal Server Error):**
```json
{
  "error": "Decryption failed: [error details]"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/decrypt \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt.gpg" \
  -o document.txt
```

---

#### Get Public Key

**`GET /get_public_key`**

Retrieves the user's public key in ASCII-armored format.

**Authentication Required:** Yes

**Response (200 OK):**
```json
{
  "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\nVersion: GnuPG v2\n\nmQENBF...\n-----END PGP PUBLIC KEY BLOCK-----"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Public key not found"
}
```

**cURL Example:**
```bash
curl -H "X-API-KEY: your_api_key" \
  http://localhost:5000/get_public_key
```

---

#### Create Challenge

**`POST /challenge`**

Creates a cryptographic challenge for user authentication.

**Authentication Required:** Yes

**Response (201 Created):**
```json
{
  "challenge": "random_challenge_string_12345",
  "challenge_id": 42
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/challenge \
  -H "X-API-KEY: your_api_key"
```

---

#### Verify Challenge

**`POST /verify_challenge`**

Verifies a signed challenge to prove key ownership.

**Authentication Required:** Yes

**Request:**
```json
{
  "challenge": "random_challenge_string_12345",
  "signature": "-----BEGIN PGP SIGNATURE-----\n...\n-----END PGP SIGNATURE-----"
}
```

**Response (200 OK):**
```json
{
  "message": "Challenge verified"
}
```

**Response (400 Bad Request):**
```json
{
  "error": "challenge and signature required"
}
```

**Response (400 Bad Request - Invalid Signature):**
```json
{
  "error": "Challenge verification failed"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/verify_challenge \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "challenge": "random_challenge_string_12345",
    "signature": "-----BEGIN PGP SIGNATURE-----\n...\n-----END PGP SIGNATURE-----"
  }'
```

---

## Error Responses

All endpoints may return the following error responses:

### 401 Unauthorized
Returned when no API key is provided for protected endpoints:
```json
{
  "error": "API key required"
}
```

### 403 Forbidden
Returned when an invalid API key is provided:
```json
{
  "error": "Invalid or inactive API key"
}
```

### 405 Method Not Allowed
Returned when using incorrect HTTP method:
```json
{
  "error": "Method not allowed"
}
```

### 500 Internal Server Error
Returned for unexpected server errors:
```json
{
  "error": "Internal server error"
}
```

---

## Usage Examples

### Complete Workflow Example

```bash
# 1. Register a new user
API_KEY=$(curl -s -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123","email":"alice@example.com"}' \
  | jq -r '.api_key')

# 2. Save public key
curl -s -H "X-API-KEY: $API_KEY" \
  http://localhost:5000/get_public_key \
  | jq -r '.public_key' > alice_public.asc

# 3. Sign a document
echo "Important document content" > document.txt
curl -X POST http://localhost:5000/sign \
  -H "X-API-KEY: $API_KEY" \
  -F "file=@document.txt" \
  -o document.txt.sig

# 4. Verify the signature
curl -X POST http://localhost:5000/verify \
  -H "X-API-KEY: $API_KEY" \
  -F "file=@document.txt.sig" \
  -F "pubkey=@alice_public.asc"

# 5. Encrypt for another user (requires their public key)
curl -X POST http://localhost:5000/encrypt \
  -H "X-API-KEY: $API_KEY" \
  -F "file=@document.txt" \
  -F "pubkey=@bob_public.asc" \
  -o document.txt.gpg

# 6. Decrypt (if you're the recipient)
curl -X POST http://localhost:5000/decrypt \
  -H "X-API-KEY: $API_KEY" \
  -F "file=@document.txt.gpg" \
  -o decrypted_document.txt
```

### File Upload Considerations

- **Maximum File Size**: Default Flask limit (16MB), can be configured
- **Supported Formats**: Any binary file format
- **File Names**: Use secure filenames to prevent path traversal attacks
- **Content Types**: Service handles binary data transparently

### Security Best Practices

1. **API Key Storage**: Store API keys securely, never in code or logs
2. **HTTPS**: Always use HTTPS in production
3. **Key Rotation**: Implement API key rotation policies
4. **Rate Limiting**: Implement rate limiting to prevent abuse
5. **File Validation**: Validate uploaded files before processing
6. **Logging**: Monitor and log all cryptographic operations

### Integration Examples

#### Python Client Example

```python
import requests
import json

class GPGWebserviceClient:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'X-API-KEY': api_key})
    
    def register(self, username, password, email):
        response = self.session.post(f'{self.base_url}/register', json={
            'username': username,
            'password': password,
            'email': email
        })
        if response.status_code == 201:
            data = response.json()
            self.api_key = data['api_key']
            self.session.headers.update({'X-API-KEY': self.api_key})
            return data
        else:
            raise Exception(f"Registration failed: {response.text}")
    
    def sign_file(self, file_path):
        with open(file_path, 'rb') as f:
            response = self.session.post(f'{self.base_url}/sign', 
                                       files={'file': f})
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Signing failed: {response.text}")
    
    def get_public_key(self):
        response = self.session.get(f'{self.base_url}/get_public_key')
        if response.status_code == 200:
            return response.json()['public_key']
        else:
            raise Exception(f"Failed to get public key: {response.text}")

# Usage
client = GPGWebserviceClient('http://localhost:5000')
user_data = client.register('alice', 'secret123', 'alice@example.com')
signature = client.sign_file('document.txt')
public_key = client.get_public_key()
```

#### JavaScript/Node.js Client Example

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

class GPGWebserviceClient {
    constructor(baseUrl, apiKey = null) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.client = axios.create({
            baseURL: baseUrl,
            headers: apiKey ? { 'X-API-KEY': apiKey } : {}
        });
    }

    async register(username, password, email) {
        try {
            const response = await this.client.post('/register', {
                username,
                password,
                email
            });
            this.apiKey = response.data.api_key;
            this.client.defaults.headers['X-API-KEY'] = this.apiKey;
            return response.data;
        } catch (error) {
            throw new Error(`Registration failed: ${error.response.data.error}`);
        }
    }

    async signFile(filePath) {
        const formData = new FormData();
        formData.append('file', fs.createReadStream(filePath));
        
        try {
            const response = await this.client.post('/sign', formData, {
                headers: formData.getHeaders(),
                responseType: 'arraybuffer'
            });
            return response.data;
        } catch (error) {
            throw new Error(`Signing failed: ${error.response.data.error}`);
        }
    }

    async getPublicKey() {
        try {
            const response = await this.client.get('/get_public_key');
            return response.data.public_key;
        } catch (error) {
            throw new Error(`Failed to get public key: ${error.response.data.error}`);
        }
    }
}

// Usage
(async () => {
    const client = new GPGWebserviceClient('http://localhost:5000');
    const userData = await client.register('alice', 'secret123', 'alice@example.com');
    const signature = await client.signFile('document.txt');
    const publicKey = await client.getPublicKey();
})();
```

This API reference provides comprehensive documentation for integrating with the GPG Webservice. For additional technical details, see the main README.md and technical overview documentation.
