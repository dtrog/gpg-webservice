#!/usr/bin/env node

/**
 * GPG Webservice MCP Adapter
 *
 * This MCP server wraps the Flask GPG webservice, making it accessible
 * to ChatGPT and other MCP-aware clients.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import fetch from 'node-fetch';
import { config } from 'dotenv';
import { resolve } from 'path';
import type {
  FunctionDefinition,
  FunctionDefinitionsResponse,
  FlaskResponse,
  MCPConfig,
} from './types.js';

// Load environment variables from .env file in the project root
config({ path: resolve(process.cwd(), '.env') });

/**
 * Get configuration from environment variables
 */
function getConfig(): MCPConfig {
  const gpgApiBase = process.env.GPG_API_BASE || 'http://localhost:5000';
  const gpgApiKey = process.env.GPG_API_KEY;

  // Ensure base URL doesn't have trailing slash
  const normalizedBase = gpgApiBase.endsWith('/')
    ? gpgApiBase.slice(0, -1)
    : gpgApiBase;

  return {
    gpgApiBase: normalizedBase,
    gpgApiKey,
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
function convertToMCPTool(func: FunctionDefinition): Tool {
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
function formatMCPResponse(flaskResponse: FlaskResponse): {
  content: Array<{ type: string; text?: string; data?: any }>;
  isError?: boolean;
} {
  if (flaskResponse.success) {
    // Success response with both text and structured data
    const message = flaskResponse.message || 'Operation completed successfully';

    const content: Array<{ type: string; text?: string; data?: any }> = [
      {
        type: 'text',
        text: message,
      }
    ];

    // Add structured data if present
    if (flaskResponse.data) {
      content.push({
        type: 'resource',
        data: flaskResponse.data
      });
    }

    return { content };
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
 * Main server setup
 */
async function main() {
  const config = getConfig();

  console.error('Starting GPG Webservice MCP Server...');
  console.error(`API Base URL (initial): ${config.gpgApiBase}`);
  console.error(`API Key: ${config.gpgApiKey ? '***configured***' : 'not configured'}`);

  // Fetch function definitions on startup
  let functionDefinitions: FunctionDefinition[];
  let actualBaseUrl: string;
  try {
    const result = await fetchFunctionDefinitions(config.gpgApiBase);
    functionDefinitions = result.functions;
    actualBaseUrl = result.baseUrl;
    console.error(`Loaded ${functionDefinitions.length} function definitions`);
    console.error(`Using base URL from Flask: ${actualBaseUrl}`);
  } catch (error) {
    console.error('Failed to load function definitions. Exiting.');
    process.exit(1);
  }

  // Create MCP server
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
    const apiKey = (args as any)?.api_key || config.gpgApiKey;

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

  // Start server with stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('GPG Webservice MCP Server started successfully');
}

// Run the server
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
