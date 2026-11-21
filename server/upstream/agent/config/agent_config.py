"""AWS configuration settings"""

# ============================================================================
# AWS Configuration
# ============================================================================

# AWS Region Configuration
AWS_REGION = "us-east-1"

# ============================================================================
# Bedrock Model Configuration
# ============================================================================

# Bedrock Model with cross-region inference

#BEDROCK_MODEL_ID = "global.anthropic.claude-sonnet-4-6" # Global Claude Sonnet 4.6
BEDROCK_MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0" # Global Claude Sonnet 4.5 
#BEDROCK_MODEL_ID = "global.anthropic.claude-sonnet-4-20250514-v1:0" # Global Claude Sonnet 4
#BEDROCK_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0" # US Anthropic Claude 3.7 Sonnet

# Model Parameters
MAX_TOKENS = 10000
ANTHROPIC_BETA = ["context-1m-2025-08-07"]  # Claude Sonnet 4's 1M context window

# Thinking configuration for Claude models
THINKING_CONFIG = {
    "type": "enabled",
    "budget_tokens": 4000
}

# ============================================================================
# Agent Configuration
# ============================================================================

AGENT_NAME = "aws-architect"
MAX_RETRIES = 3
SERVER_CLEANUP_TIMEOUT = 5  # seconds

# ============================================================================
# Rate Limiter Configuration
# ============================================================================

RATE_LIMIT_MAX_REQUESTS = 5  # Maximum LLM requests per time window
RATE_LIMIT_TIME_WINDOW = 60  # Time window in seconds (1 minute)



# ============================================================================
# MCP Server Configuration
# ============================================================================

# Environment variables for MCP servers
MCP_ENV_VARS = {
    "AWS_REGION": AWS_REGION,
    "BEDROCK_MODEL_ID": BEDROCK_MODEL_ID,
    "FASTMCP_LOG_LEVEL": "ERROR"
}

# MCP Server Definitions
MCP_SERVERS = [
    {
        "name": "AWS Knowledge",
        "client_type": "http",
        "url": "https://knowledge-mcp.global.api.aws",
        "remote": True
    },
    {
        "name": "AWS Pricing",
        "client_type": "stdio",
        "command": "uvx",
        "args": ["awslabs.aws-pricing-mcp-server@latest"],
        "remote": True
    },
    {
        "name": "AWS Diagram",
        "client_type": "stdio",
        "command": "uvx",
        "args": ["awslabs.aws-diagram-mcp-server@latest"],
        "env": {"FASTMCP_LOG_LEVEL": "ERROR", "AWS_REGION": AWS_REGION},
        "remote": True
    }
]
