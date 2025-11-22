/**
 * Unit tests for GPG Webservice MCP Server
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import request from 'supertest';
import { getConfig, convertToMCPTool, formatMCPResponse, createApp } from './http-server.js';
import type { FunctionDefinition, FlaskResponse } from './types.js';

describe('getConfig', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should return default values when env vars are not set', () => {
    delete process.env.GPG_API_BASE;
    delete process.env.GPG_API_KEY;
    delete process.env.MCP_PORT;
    delete process.env.MCP_HOST;

    const config = getConfig();

    expect(config.gpgApiBase).toBe('http://localhost:5000');
    expect(config.gpgApiKey).toBeUndefined();
    expect(config.port).toBe(3000);
    expect(config.host).toBe('0.0.0.0');
  });

  it('should use environment variables when set', () => {
    process.env.GPG_API_BASE = 'http://custom-api:8080';
    process.env.GPG_API_KEY = 'test-api-key';
    process.env.MCP_PORT = '4000';
    process.env.MCP_HOST = '127.0.0.1';

    const config = getConfig();

    expect(config.gpgApiBase).toBe('http://custom-api:8080');
    expect(config.gpgApiKey).toBe('test-api-key');
    expect(config.port).toBe(4000);
    expect(config.host).toBe('127.0.0.1');
  });

  it('should normalize base URL by removing trailing slash', () => {
    process.env.GPG_API_BASE = 'http://api.example.com/';

    const config = getConfig();

    expect(config.gpgApiBase).toBe('http://api.example.com');
  });

  it('should not modify base URL without trailing slash', () => {
    process.env.GPG_API_BASE = 'http://api.example.com';

    const config = getConfig();

    expect(config.gpgApiBase).toBe('http://api.example.com');
  });
});

describe('convertToMCPTool', () => {
  it('should convert a Flask function definition to MCP tool format', () => {
    const funcDef: FunctionDefinition = {
      name: 'sign_text',
      description: 'Sign text with GPG key',
      parameters: {
        type: 'object',
        properties: {
          text: {
            type: 'string',
            description: 'Text to sign',
          },
        },
        required: ['text'],
      },
    };

    const tool = convertToMCPTool(funcDef);

    expect(tool.name).toBe('sign_text');
    expect(tool.description).toBe('Sign text with GPG key');
    expect(tool.inputSchema).toEqual({
      type: 'object',
      properties: {
        text: {
          type: 'string',
          description: 'Text to sign',
        },
      },
      required: ['text'],
    });
  });

  it('should handle function with multiple parameters', () => {
    const funcDef: FunctionDefinition = {
      name: 'register_user',
      description: 'Register a new user',
      parameters: {
        type: 'object',
        properties: {
          username: {
            type: 'string',
            description: 'Username',
            minLength: 3,
            maxLength: 50,
          },
          password: {
            type: 'string',
            description: 'Password',
            minLength: 8,
          },
          email: {
            type: 'string',
            description: 'Email address',
            format: 'email',
          },
        },
        required: ['username', 'password', 'email'],
      },
    };

    const tool = convertToMCPTool(funcDef);

    expect(tool.name).toBe('register_user');
    expect(tool.inputSchema.required).toEqual(['username', 'password', 'email']);
    expect(Object.keys(tool.inputSchema.properties || {})).toHaveLength(3);
  });

  it('should handle function with no required parameters', () => {
    const funcDef: FunctionDefinition = {
      name: 'get_status',
      description: 'Get current status',
      parameters: {
        type: 'object',
        properties: {},
        required: [],
      },
    };

    const tool = convertToMCPTool(funcDef);

    expect(tool.inputSchema.required).toEqual([]);
  });
});

describe('formatMCPResponse', () => {
  it('should format successful response with message only', () => {
    const flaskResponse: FlaskResponse = {
      success: true,
      message: 'Operation completed',
    };

    const result = formatMCPResponse(flaskResponse);

    expect(result.isError).toBeUndefined();
    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe('text');
    expect(result.content[0].text).toBe('Operation completed');
  });

  it('should format successful response with data', () => {
    const flaskResponse: FlaskResponse = {
      success: true,
      message: 'User registered',
      data: {
        user_id: 1,
        public_key: '-----BEGIN PGP PUBLIC KEY-----',
      },
    };

    const result = formatMCPResponse(flaskResponse);

    expect(result.isError).toBeUndefined();
    expect(result.content).toHaveLength(2);
    expect(result.content[0].type).toBe('text');
    expect(result.content[0].text).toBe('User registered');
    expect(result.content[1].type).toBe('resource');
    expect(result.content[1].data).toEqual({
      user_id: 1,
      public_key: '-----BEGIN PGP PUBLIC KEY-----',
    });
  });

  it('should use default message when not provided', () => {
    const flaskResponse: FlaskResponse = {
      success: true,
    };

    const result = formatMCPResponse(flaskResponse);

    expect(result.content[0].text).toBe('Operation completed successfully');
  });

  it('should format error response', () => {
    const flaskResponse: FlaskResponse = {
      success: false,
      error: 'Invalid API key',
      error_code: 'AUTH_ERROR',
    };

    const result = formatMCPResponse(flaskResponse);

    expect(result.isError).toBe(true);
    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe('text');
    expect(result.content[0].text).toBe('Error: Invalid API key\nError Code: AUTH_ERROR');
  });

  it('should use default error values when not provided', () => {
    const flaskResponse: FlaskResponse = {
      success: false,
    };

    const result = formatMCPResponse(flaskResponse);

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toBe('Error: Operation failed with unknown error\nError Code: UNKNOWN_ERROR');
  });

  it('should handle network error response', () => {
    const flaskResponse: FlaskResponse = {
      success: false,
      error: 'Network error: Connection refused',
      error_code: 'NETWORK_ERROR',
    };

    const result = formatMCPResponse(flaskResponse);

    expect(result.isError).toBe(true);
    expect(result.content[0].text).toContain('Network error');
    expect(result.content[0].text).toContain('NETWORK_ERROR');
  });
});

describe('HTTP Endpoints', () => {
  const mockFunctionDefinitions: FunctionDefinition[] = [
    {
      name: 'sign_text',
      description: 'Sign text with GPG key',
      parameters: {
        type: 'object',
        properties: {
          text: { type: 'string', description: 'Text to sign' },
        },
        required: ['text'],
      },
    },
    {
      name: 'register_user',
      description: 'Register a new user',
      parameters: {
        type: 'object',
        properties: {
          username: { type: 'string', description: 'Username' },
          password: { type: 'string', description: 'Password' },
          email: { type: 'string', description: 'Email' },
        },
        required: ['username', 'password', 'email'],
      },
    },
  ];

  describe('GET /health', () => {
    it('should return health status with correct structure', async () => {
      const app = createApp(mockFunctionDefinitions, 'http://localhost:5555');

      const response = await request(app).get('/health');

      expect(response.status).toBe(200);
      expect(response.body).toEqual({
        status: 'healthy',
        service: 'gpg-webservice-mcp',
        version: '1.0.0',
        transport: 'http',
        tools_loaded: 2,
      });
    });

    it('should report correct number of tools loaded', async () => {
      const singleTool: FunctionDefinition[] = [mockFunctionDefinitions[0]];
      const app = createApp(singleTool, 'http://localhost:5555');

      const response = await request(app).get('/health');

      expect(response.body.tools_loaded).toBe(1);
    });

    it('should report zero tools when none configured', async () => {
      const app = createApp([], 'http://localhost:5555');

      const response = await request(app).get('/health');

      expect(response.body.tools_loaded).toBe(0);
    });
  });

  describe('POST /mcp', () => {
    it('should accept POST requests to /mcp endpoint', async () => {
      const app = createApp(mockFunctionDefinitions, 'http://localhost:5555');

      // The MCP endpoint expects a specific protocol format
      // This test just verifies the endpoint exists and accepts requests
      const response = await request(app)
        .post('/mcp')
        .send({})
        .set('Content-Type', 'application/json');

      // MCP endpoint will return an error for invalid requests, but should not 404
      expect(response.status).not.toBe(404);
    });
  });
});
