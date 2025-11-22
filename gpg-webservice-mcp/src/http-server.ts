#!/usr/bin/env node

/**
 * GPG Webservice MCP Adapter - HTTP Transport
 *
 * This MCP server wraps the Flask GPG webservice using HTTP transport,
 * making it accessible to ChatGPT and other MCP clients over the network.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import express, { Request, Response } from 'express';
import fetch from 'node-fetch';
import { config } from 'dotenv';
import type {
  FunctionDefinition,
  FunctionDefinitionsResponse,
  FlaskResponse,
  MCPConfig,
} from './types.js';

// Load environment variables
config();

/**
 * Get configuration from environment variables
 */
export function getConfig(): MCPConfig & { port: number; host: string } {
  const gpgApiBase = process.env.GPG_API_BASE || 'http://localhost:5000';
  const gpgApiKey = process.env.GPG_API_KEY;
  const port = parseInt(process.env.MCP_PORT || '3000', 10);
  const host = process.env.MCP_HOST || '0.0.0.0';

  // Ensure base URL doesn't have trailing slash
  const normalizedBase = gpgApiBase.endsWith('/')
    ? gpgApiBase.slice(0, -1)
    : gpgApiBase;

  return {
    gpgApiBase: normalizedBase,
    gpgApiKey,
    port,
    host,
  };
}

/**
 * Fetch function definitions from the Flask GPG webservice
 * Returns both the function definitions and the base_url from the response
 */
async function fetchFunctionDefinitions(
  baseUrl: string
): Promise<{ functions: FunctionDefinition[]; baseUrl: string }> {
  const url = `${baseUrl}/openai/function_definitions`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(
        `Failed to fetch function definitions: ${response.status} ${response.statusText}`
      );
    }

    const data = (await response.json()) as FunctionDefinitionsResponse;

    if (!data.success || !data.data?.functions) {
      throw new Error('Invalid response from function_definitions endpoint');
    }

    // Use the base_url returned by Flask, or fall back to the configured base
    const flaskBaseUrl = data.data.base_url
      ? (data.data.base_url.endsWith('/')
          ? data.data.base_url.slice(0, -1)
          : data.data.base_url)
      : baseUrl;

    return {
      functions: data.data.functions,
      baseUrl: flaskBaseUrl
    };
  } catch (error) {
    console.error('Error fetching function definitions:', error);
    throw error;
  }
}

/**
 * Convert Flask function definition to MCP tool definition
 */
export function convertToMCPTool(func: FunctionDefinition): Tool {
  return {
    name: func.name,
    description: func.description,
    inputSchema: {
      type: 'object',
      properties: func.parameters.properties,
      required: func.parameters.required,
    },
  };
}

/**
 * Call a Flask GPG webservice endpoint
 */
async function callFlaskEndpoint(
  baseUrl: string,
  functionName: string,
  parameters: Record<string, any>,
  apiKey?: string
): Promise<FlaskResponse> {
  const url = `${baseUrl}/openai/${functionName}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Add API key if provided (either from environment or tool parameters)
  if (apiKey) {
    headers['X-API-KEY'] = apiKey;
  }

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(parameters),
    });

    const data = (await response.json()) as FlaskResponse;

    // Return the full response, including error information if present
    return {
      ...data,
      // Add HTTP status for context
      ...(response.status !== 200 && { http_status: response.status }),
    };
  } catch (error) {
    console.error(`Error calling ${functionName}:`, error);
    return {
      success: false,
      error: `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      error_code: 'NETWORK_ERROR',
    };
  }
}

/**
 * Format Flask response for MCP client
 * Returns both human-readable text and structured JSON content
 */
export function formatMCPResponse(flaskResponse: FlaskResponse): {
  content: Array<{ type: string; text?: string; data?: any }>;
  isError?: boolean;
} {
  if (flaskResponse.success) {
    // Success response with both text and structured data
    const message = flaskResponse.message || 'Operation completed successfully';

    let textContent = message;

    // Add structured data as JSON text if present
    if (flaskResponse.data) {
      textContent += '\n\n' + JSON.stringify(flaskResponse.data, null, 2);
    }

    return {
      content: [
        {
          type: 'text',
          text: textContent,
        }
      ]
    };
  } else {
    // Error response
    const errorMessage =
      flaskResponse.error || 'Operation failed with unknown error';
    const errorCode = flaskResponse.error_code || 'UNKNOWN_ERROR';

    return {
      content: [
        {
          type: 'text',
          text: `Error: ${errorMessage}\nError Code: ${errorCode}`,
        },
      ],
      isError: true,
    };
  }
}

/**
 * Create an MCP server instance with handlers
 */
function createMCPServer(
  functionDefinitions: FunctionDefinition[],
  actualBaseUrl: string,
  configApiKey?: string
): Server {
  const server = new Server(
    {
      name: 'gpg-webservice-mcp',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // Register list_tools handler
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const tools = functionDefinitions.map(convertToMCPTool);
    return { tools };
  });

  // Register call_tool handler
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    // Find the function definition
    const funcDef = functionDefinitions.find((f) => f.name === name);
    if (!funcDef) {
      return {
        content: [
          {
            type: 'text',
            text: `Error: Unknown tool "${name}"`,
          },
        ],
        isError: true,
      };
    }

    // Extract API key from arguments if provided, otherwise use environment variable
    const apiKey = (args as any)?.api_key || configApiKey;

    // Remove api_key from parameters before sending to Flask
    // (it's sent in the header instead)
    const parameters = { ...(args as Record<string, any>) };
    delete parameters.api_key;

    // Call the Flask endpoint using the base URL from Flask
    const flaskResponse = await callFlaskEndpoint(
      actualBaseUrl,
      name,
      parameters,
      apiKey
    );

    // Format and return the response
    return formatMCPResponse(flaskResponse);
  });

  return server;
}

/**
 * Create Express app with routes (exported for testing)
 */
export function createApp(
  functionDefinitions: FunctionDefinition[],
  actualBaseUrl: string,
  configApiKey?: string
): express.Express {
  const app = express();
  app.use(express.json());

  // Health check endpoint
  app.get('/health', (req: Request, res: Response) => {
    res.json({
      status: 'healthy',
      service: 'gpg-webservice-mcp',
      version: '1.0.0',
      transport: 'http',
      tools_loaded: functionDefinitions.length,
    });
  });

  // MCP endpoint - create new transport for each request
  app.post('/mcp', async (req: Request, res: Response) => {
    try {
      // Create a new MCP server instance for this request
      const server = createMCPServer(
        functionDefinitions,
        actualBaseUrl,
        configApiKey
      );

      // Create a new transport for this request to prevent ID collisions
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
        enableJsonResponse: true,
      });

      // Clean up transport when response closes
      res.on('close', () => {
        transport.close();
      });

      // Connect server to transport
      await server.connect(transport);

      // Handle the MCP request
      await transport.handleRequest(req, res, req.body);
    } catch (error) {
      console.error('Error handling MCP request:', error);
      if (!res.headersSent) {
        res.status(500).json({
          error: 'Internal server error',
          message: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }
  });

  return app;
}

/**
 * Main HTTP server setup
 */
async function main() {
  const appConfig = getConfig();

  console.log('Starting GPG Webservice MCP Server (HTTP Transport)...');
  console.log(`API Base URL (initial): ${appConfig.gpgApiBase}`);
  console.log(`API Key: ${appConfig.gpgApiKey ? '***configured***' : 'not configured'}`);
  console.log(`HTTP Server: ${appConfig.host}:${appConfig.port}`);

  // Fetch function definitions on startup
  let functionDefinitions: FunctionDefinition[];
  let actualBaseUrl: string;
  try {
    const result = await fetchFunctionDefinitions(appConfig.gpgApiBase);
    functionDefinitions = result.functions;
    actualBaseUrl = result.baseUrl;
    console.log(`Loaded ${functionDefinitions.length} function definitions`);
    console.log(`Using base URL from Flask: ${actualBaseUrl}`);
  } catch (error) {
    console.error('Failed to load function definitions. Exiting.');
    process.exit(1);
  }

  // Create and configure app
  const app = createApp(functionDefinitions, actualBaseUrl, appConfig.gpgApiKey);

  // Start HTTP server
  app.listen(appConfig.port, appConfig.host, () => {
    console.log(`\nGPG Webservice MCP Server listening on http://${appConfig.host}:${appConfig.port}`);
    console.log(`MCP endpoint: http://${appConfig.host}:${appConfig.port}/mcp`);
    console.log(`Health check: http://${appConfig.host}:${appConfig.port}/health`);
    console.log('\nReady to accept MCP connections from ChatGPT and other clients\n');
  });
}

// Run the server only when executed directly (not when imported for testing)
const isMainModule = process.argv[1]?.endsWith('http-server.js') ||
                     process.argv[1]?.endsWith('http-server.ts');

if (isMainModule) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}
