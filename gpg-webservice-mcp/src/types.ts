/**
 * Type definitions for GPG Webservice MCP adapter
 */

/**
 * Function definition as returned by the Flask /openai/function_definitions endpoint
 */
export interface FunctionDefinition {
  name: string;
  description: string;
  parameters: {
    type: 'object';
    properties: Record<string, ParameterProperty>;
    required: string[];
  };
}

/**
 * JSON Schema property definition
 */
export interface ParameterProperty {
  type: string;
  description: string;
  minLength?: number;
  maxLength?: number;
  format?: string;
}

/**
 * Response from /openai/function_definitions endpoint
 */
export interface FunctionDefinitionsResponse {
  success: boolean;
  data: {
    functions: FunctionDefinition[];
    base_url: string;
    authentication: string;
    rate_limits: {
      api_endpoints: string;
    };
  };
  message: string;
}

/**
 * Standard Flask API response format
 */
export interface FlaskResponse {
  success: boolean;
  data?: any;
  error?: string;
  error_code?: string;
  message?: string;
}

/**
 * MCP server configuration
 */
export interface MCPConfig {
  gpgApiBase: string;
  gpgApiKey?: string;
}
