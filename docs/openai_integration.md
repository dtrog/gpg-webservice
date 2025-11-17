# OpenAI Function Calling Integration

This document provides comprehensive guidance for using the GPG Webservice with OpenAI's function calling feature. The service provides structured endpoints that are compatible with OpenAI's function calling system.

## Overview

The GPG Webservice includes specialized endpoints under `/openai/` that are designed to work seamlessly with OpenAI's function calling feature. These endpoints:

- Accept structured JSON inputs compatible with OpenAI function parameters
- Return structured JSON responses with consistent success/error formats
- Include comprehensive error codes for proper error handling
- Support all core GPG operations (sign, verify, encrypt, decrypt)

## Function Definitions

Get all available function definitions:

```bash
curl -X GET http://localhost:5000/openai/function_definitions
```

This returns the complete OpenAI function calling schema for all available functions.

## Available Functions

### 1. register_user

Register a new user with automatic GPG key generation.

**OpenAI Function Definition:**
```json
{
  "name": "register_user",
  "description": "Register a new user account with automatic GPG key generation",
  "parameters": {
    "type": "object",
    "properties": {
      "username": {
        "type": "string",
        "description": "Username (3-50 chars, alphanumeric + underscore/hyphen)",
        "minLength": 3,
        "maxLength": 50
      },
      "password": {
        "type": "string", 
        "description": "Strong password (8+ chars, uppercase, lowercase, digit, special char)",
        "minLength": 8
      },
      "email": {
        "type": "string",
        "description": "Valid email address",
        "format": "email"
      }
    },
    "required": ["username", "password", "email"]
  }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/openai/register_user \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice_ai",
    "password": "SecurePass123!",
    "email": "alice@example.com"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "username": "alice_ai",
    "api_key": "abc123...",
    "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----..."
  },
  "message": "User registered successfully"
}
```

### 2. sign_text

Sign text content using the user's private GPG key.

**OpenAI Function Definition:**
```json
{
  "name": "sign_text",
  "description": "Sign text content using the user's private GPG key",
  "parameters": {
    "type": "object",
    "properties": {
      "text": {
        "type": "string",
        "description": "Text content to sign"
      }
    },
    "required": ["text"]
  }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/openai/sign_text \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "text": "This is a confidential message that needs to be signed."
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "signature": "iQEcBAABCAAGBQJh...",
    "text_signed": "This is a confidential message that needs to be signed.",
    "signature_format": "base64"
  },
  "message": "Text signed successfully"
}
```

### 3. verify_text_signature

Verify a text signature against a public key.

**OpenAI Function Definition:**
```json
{
  "name": "verify_text_signature",
  "description": "Verify a text signature against a public key",
  "parameters": {
    "type": "object",
    "properties": {
      "text": {
        "type": "string",
        "description": "Original text content that was signed"
      },
      "signature": {
        "type": "string",
        "description": "Base64-encoded signature"
      },
      "public_key": {
        "type": "string",
        "description": "ASCII-armored public key for verification"
      }
    },
    "required": ["text", "signature", "public_key"]
  }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/openai/verify_text_signature \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "text": "This is a confidential message that needs to be signed.",
    "signature": "iQEcBAABCAAGBQJh...",
    "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----..."
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "verified": true,
    "text_verified": "This is a confidential message that needs to be signed.",
    "signature_valid": true
  },
  "message": "Signature verification successful"
}
```

### 4. encrypt_text

Encrypt text content for a recipient using their public key.

**OpenAI Function Definition:**
```json
{
  "name": "encrypt_text",
  "description": "Encrypt text content for a recipient using their public key",
  "parameters": {
    "type": "object",
    "properties": {
      "text": {
        "type": "string",
        "description": "Text content to encrypt"
      },
      "recipient_public_key": {
        "type": "string",
        "description": "ASCII-armored public key of the recipient"
      }
    },
    "required": ["text", "recipient_public_key"]
  }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/openai/encrypt_text \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "text": "Secret message for Bob",
    "recipient_public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----..."
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "encrypted_text": "hQEMA5vJH8t1J...",
    "original_text_length": 21,
    "format": "base64"
  },
  "message": "Text encrypted successfully"
}
```

### 5. decrypt_text

Decrypt text content using the user's private key.

**OpenAI Function Definition:**
```json
{
  "name": "decrypt_text",
  "description": "Decrypt text content using the user's private key",
  "parameters": {
    "type": "object",
    "properties": {
      "encrypted_text": {
        "type": "string",
        "description": "Base64-encoded encrypted content"
      }
    },
    "required": ["encrypted_text"]
  }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/openai/decrypt_text \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "encrypted_text": "hQEMA5vJH8t1J..."
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "decrypted_text": "Secret message for Bob",
    "text_length": 21
  },
  "message": "Text decrypted successfully"
}
```

### 6. get_user_public_key

Get the authenticated user's public GPG key.

**OpenAI Function Definition:**
```json
{
  "name": "get_user_public_key",
  "description": "Get the authenticated user's public GPG key",
  "parameters": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:5000/openai/get_user_public_key \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{}'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "public_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----...",
    "username": "alice_ai",
    "key_format": "ASCII-armored"
  },
  "message": "Public key retrieved successfully"
}
```

## OpenAI Integration Example

Here's how to use these functions with OpenAI's API:

### Python Example

```python
import openai
import requests
import json

# Configure OpenAI
openai.api_key = "your-openai-api-key"

# Function definitions for OpenAI
functions = [
    {
        "name": "register_user",
        "description": "Register a new user account with automatic GPG key generation",
        "parameters": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Username (3-50 chars)"},
                "password": {"type": "string", "description": "Strong password (8+ chars)"},
                "email": {"type": "string", "description": "Valid email address"}
            },
            "required": ["username", "password", "email"]
        }
    },
    {
        "name": "sign_text",
        "description": "Sign text content using user's private GPG key",
        "parameters": {
            "type": "object", 
            "properties": {
                "text": {"type": "string", "description": "Text content to sign"}
            },
            "required": ["text"]
        }
    },
    # ... other function definitions
]

def call_gpg_function(function_name, arguments, api_key=None):
    """Call a GPG webservice function"""
    url = f"http://localhost:5000/openai/{function_name}"
    headers = {"Content-Type": "application/json"}
    
    if api_key:
        headers["X-API-KEY"] = api_key
        
    response = requests.post(url, json=arguments, headers=headers)
    return response.json()

# Example: Using OpenAI to orchestrate GPG operations
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {
            "role": "user", 
            "content": "Register a new user named 'ai_assistant' with email 'ai@example.com' and password 'SecureAI123!' then sign the text 'Hello from AI'"
        }
    ],
    functions=functions,
    function_call="auto"
)

# Handle function calls
if response.choices[0].message.get("function_call"):
    function_call = response.choices[0].message["function_call"]
    function_name = function_call["name"]
    arguments = json.loads(function_call["arguments"])
    
    # Call the actual GPG service
    result = call_gpg_function(function_name, arguments)
    
    # If this was user registration, extract API key for subsequent calls
    if function_name == "register_user" and result.get("success"):
        api_key = result["data"]["api_key"]
        
        # Now call sign_text with the new API key
        sign_result = call_gpg_function(
            "sign_text", 
            {"text": "Hello from AI"}, 
            api_key=api_key
        )
        
        print("Registration:", result)
        print("Signing:", sign_result)
```

### JavaScript/Node.js Example

```javascript
const { OpenAI } = require('openai');
const axios = require('axios');

const openai = new OpenAI({
    apiKey: 'your-openai-api-key'
});

async function callGPGFunction(functionName, arguments, apiKey = null) {
    const url = `http://localhost:5000/openai/${functionName}`;
    const headers = { 'Content-Type': 'application/json' };
    
    if (apiKey) {
        headers['X-API-KEY'] = apiKey;
    }
    
    try {
        const response = await axios.post(url, arguments, { headers });
        return response.data;
    } catch (error) {
        return { success: false, error: error.message };
    }
}

async function main() {
    const functions = [
        {
            name: "register_user",
            description: "Register a new user account with automatic GPG key generation",
            parameters: {
                type: "object",
                properties: {
                    username: { type: "string", description: "Username (3-50 chars)" },
                    password: { type: "string", description: "Strong password (8+ chars)" },
                    email: { type: "string", description: "Valid email address" }
                },
                required: ["username", "password", "email"]
            }
        },
        // ... other functions
    ];
    
    const completion = await openai.chat.completions.create({
        model: "gpt-4",
        messages: [{
            role: "user",
            content: "Register user 'js_bot' with email 'bot@example.com' and password 'JSBot123!' then get their public key"
        }],
        functions: functions,
        function_call: "auto"
    });
    
    if (completion.choices[0].message.function_call) {
        const { name, arguments: args } = completion.choices[0].message.function_call;
        const parsedArgs = JSON.parse(args);
        
        const result = await callGPGFunction(name, parsedArgs);
        console.log('Function result:', result);
        
        if (name === 'register_user' && result.success) {
            // Get public key with the new API key
            const publicKeyResult = await callGPGFunction(
                'get_user_public_key', 
                {}, 
                result.data.api_key
            );
            console.log('Public key:', publicKeyResult);
        }
    }
}

main().catch(console.error);
```

## Error Handling

All endpoints return structured error responses:

```json
{
  "success": false,
  "error": "Descriptive error message",
  "error_code": "ERROR_CODE_CONSTANT"
}
```

### Common Error Codes

- `AUTH_REQUIRED`: API key is missing
- `AUTH_INVALID`: API key is invalid
- `INVALID_INPUT`: Request data is malformed
- `MISSING_FIELDS`: Required fields are missing
- `KEY_NOT_FOUND`: GPG key not found for user
- `SIGNING_FAILED`: GPG signing operation failed
- `ENCRYPTION_FAILED`: GPG encryption operation failed
- `DECRYPTION_FAILED`: GPG decryption operation failed
- `VERIFICATION_FAILED`: Signature verification failed
- `INTERNAL_ERROR`: Unexpected server error

## Security Considerations

### Authentication
- All endpoints (except `register_user` and `function_definitions`) require API key authentication
- API keys are provided via the `X-API-KEY` header
- API keys are obtained through user registration

### Rate Limiting
- All endpoints are subject to rate limiting (30 requests/minute per IP)
- Rate limiting errors return HTTP 429 with error code `RATE_LIMIT_EXCEEDED`

### Input Validation
- All inputs are validated according to security requirements
- Text content has reasonable size limits to prevent abuse
- Base64 encoding/decoding is validated for format correctness

### Data Handling
- All cryptographic operations use temporary files that are automatically cleaned up
- No sensitive data is logged or stored beyond the necessary database records
- All GPG operations are performed in isolated temporary environments

## Best Practices

### OpenAI Function Integration
1. **Error Handling**: Always check the `success` field in responses
2. **API Key Management**: Store API keys securely after user registration
3. **Function Chaining**: Use results from one function as inputs to another
4. **Validation**: Validate function arguments before making calls

### Security
1. **HTTPS**: Use HTTPS in production environments
2. **API Key Storage**: Never log or expose API keys
3. **Input Sanitization**: Validate all user inputs before processing
4. **Rate Limiting**: Implement client-side rate limiting to avoid 429 errors

### Performance
1. **Batch Operations**: Group related operations when possible
2. **Caching**: Cache public keys when performing multiple operations
3. **Error Recovery**: Implement retry logic with exponential backoff
4. **Resource Cleanup**: Ensure proper cleanup of temporary resources

This OpenAI integration provides a powerful way to incorporate GPG cryptographic operations into AI-powered applications, enabling secure communication and data protection workflows.