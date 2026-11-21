# AtForma modification: package-relative file writer import. MIT-0 upstream preserved.
import logging
import sys
import os
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from io import StringIO
from contextlib import contextmanager
from dataclasses import dataclass
from strands import Agent
from strands.models import BedrockModel
from strands.session.file_session_manager import FileSessionManager
from strands.tools.mcp import MCPClient
from .config.prompts import SYSTEM_INSTRUCTIONS
from .config.agent_config import BEDROCK_MODEL_ID, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_TIME_WINDOW, MAX_TOKENS, THINKING_CONFIG, ANTHROPIC_BETA
from ..utils.file_writer import write_file
from .rate_limiter import RateLimiter



logger = logging.getLogger(__name__) #module level logger

# Configure Strands logging
logging.getLogger("strands.tools.registry").setLevel(logging.ERROR) # VD : log tool registration
logging.getLogger("strands.models").setLevel(logging.ERROR) #VD : log model invocation 
logging.getLogger("strands.event_loop").setLevel(logging.ERROR) # VD : log event loop , how the agent is thinking  

@dataclass
class MCPServerConfig:
    """Configuration for MCP servers"""
    name: str
    client_type: str
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    remote: bool = False

class LogCapture:
    """Simplified log capture utility with streaming support"""
    def __init__(self, stream_callback=None):
        self.log_stream = StringIO()
        self.stream_callback = stream_callback
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.DEBUG)
        
        # Custom formatter to preserve full message
        class FullMessageFormatter(logging.Formatter):
            def format(self, record):
                msg = str(record.getMessage())
                return f"{self.formatTime(record)} - {record.levelname}: {msg}"
        
        formatter = FullMessageFormatter()
        self.handler.setFormatter(formatter)
        
        # Override emit to stream logs in real-time
        original_emit = self.handler.emit
        def streaming_emit(record):
            original_emit(record)
            if self.stream_callback:
                self.stream_callback(self.handler.format(record))
        self.handler.emit = streaming_emit
    
    @contextmanager
    def capture(self):
        """Context manager for filtered stdout/stderr capture"""
        # Capture stdout/stderr
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        class FilteredTeeStream:
            def __init__(self, original, capture_stream, filter_func=None):
                self.original = original
                self.capture_stream = capture_stream
                self.filter_func = filter_func
            
            def write(self, text):
                self.original.write(text)
                if self.filter_func is None or self.filter_func(text):
                    self.capture_stream.write(text)
            
            def flush(self):
                self.original.flush()
                self.capture_stream.flush()
        
        # Filter function for stdout - only capture lines starting with "Tool"
        def stdout_filter(text):
            return text.strip().startswith("Tool")
        
        sys.stdout = FilteredTeeStream(original_stdout, self.log_stream, stdout_filter)
        sys.stderr = FilteredTeeStream(original_stderr, self.log_stream)  # Capture all stderr
        
        self.log_stream.seek(0)
        self.log_stream.truncate(0)
        
        try:
            yield self
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
    
    def get_logs(self) -> str:
        return self.log_stream.getvalue()



class MCPClientManager:
    """Manages MCP client connections and tools"""
    
    def __init__(self):
        self.clients = {}
        self.config = self._get_default_config()
        self.server_processes = []
        self.clients_activated = False
        # Cache connection status and tools during initialization for UI display
        self.connection_status = {}  # server_name -> status string
        self.server_tools = {}       # server_name -> list of tools
    
    def _get_default_config(self) -> List[MCPServerConfig]:
        """Default MCP server configurations"""
        return [
            MCPServerConfig(
                name="AWS Knowledge",
                client_type="http",
                url="https://knowledge-mcp.global.api.aws",
                remote=True
            ),
            MCPServerConfig(
                name="AWS Pricing",
                client_type="stdio",
                command="uvx",
                args=["awslabs.aws-pricing-mcp-server@latest"],
                remote=True
            ),
            MCPServerConfig(
                name="AWS Diagram",
                client_type="stdio",
                command="uvx",
                args=["awslabs.aws-diagram-mcp-server@latest"],
                env={"FASTMCP_LOG_LEVEL": "ERROR", "AWS_REGION": "us-east-1"},
                remote=True
            ),
            # MCPServerConfig(
            #     name="Local Diagram Samples",
            #     client_type="stdio",
            #     command="python",
            #     args=["local_mcp_servers/sample_diagrams/server.py"],
            #     remote=False
            # ),
            # MCPServerConfig(
            #     name="Local WAR Samples",
            #     client_type="stdio",
            #     command="python",
            #     args=["local_mcp_servers/war_assessment/server.py"],
            #     remote=False
            # )
        ]
    
    def initialize_clients(self) -> Dict[str, Any]:
        """Initialize all MCP clients"""
        from mcp.client.streamable_http import streamablehttp_client
        from mcp import stdio_client, StdioServerParameters
        import subprocess
        import time
        
        self._start_local_servers()
        
        for config in self.config:
            try:
                if config.client_type == "http":
                    client = MCPClient(lambda url=config.url: streamablehttp_client(url))
                elif config.client_type == "stdio":
                    client = MCPClient(lambda cfg=config: stdio_client(
                        StdioServerParameters(
                            command=cfg.command,
                            args=cfg.args,
                            env=cfg.env or {}
                        )
                    ))
                else:
                    logger.error(f"Unknown client type: {config.client_type}")
                    continue
                
                if self._validate_connectivity(client, config.name):
                    self.clients[config.name] = client
                else:
                    # Status already cached in _validate_connectivity
                    pass
                    
            except Exception as e:
                # Cache initialization failure status
                self.connection_status[config.name] = "🔴 Disconnected"
                self.server_tools[config.name] = []
                logger.error(f"{config.name} MCP client failed: {e}")
        
        logger.info(f"MCP Status: {len(self.clients)}/{len(self.config)} servers connected")
        
        # Log detailed connection status for each server
        for config in self.config:
            if config.name in self.clients:
                logger.info(f"✅ MCP Server '{config.name}': Connected successfully")
            else:
                logger.error(f"❌ MCP Server '{config.name}': Failed to connect")
        
        return self.clients
    
    def _start_local_servers(self):
        """Start local MCP servers as background processes"""
        import subprocess
        import time
        
        self.server_processes = []
        
        
    def _validate_connectivity(self, client, name: str) -> bool:
        """Validate MCP client connectivity and cache status + tools for UI"""
        try:
            with client:
                tools = client.list_tools_sync()
                # Cache successful connection status and tools
                self.connection_status[name] = "🟢 Connected"
                self.server_tools[name] = tools
                logger.info(f"{name} server: Connected")
                return True
        except Exception as e:
            # Cache failed connection status
            self.connection_status[name] = "🟡 Error"
            self.server_tools[name] = []
            logger.error(f"{name} server: Connection failed - {e}")
            return False
    
    def load_tools(self) -> List[Any]:
        """Load tools from all connected MCP clients"""
        tools = []
        logger.info(f"Starting tool loading from {len(self.clients)} connected clients...")
        
        for name, client in self.clients.items():
            try:
                logger.info(f"Loading tools from {name} server...")
                logger.info(f"Client type: {type(client)}")
                
                with client:
                    client_tools = client.list_tools_sync()
                    logger.info(f"Raw tools from {name}: {len(client_tools)} tools")
                    
                    tools.extend(client_tools)
                    logger.info(f"✅ {name} server: {len(client_tools)} tools loaded")
            except AttributeError as e:
                logger.error(f"❌ {name} server: Method not found - {e}")
            except Exception as e:
                logger.error(f"❌ {name} server tools failed: {e}")
        
        logger.info(f"Tools Status: {len(tools)} total tools loaded")
        return tools
    
    @contextmanager
    def active_clients(self):
        """Context manager for active MCP clients"""
        if not self.clients_activated:
            entered_clients = []
            try:
                for name, client in self.clients.items():
                    try:
                        client.__enter__()
                        entered_clients.append(client)
                        logger.info(f"Activated MCP client: {name}")
                    except Exception as e:
                        logger.error(f"Failed to activate {name} client: {e}")
                
                self.clients_activated = True
                yield self.clients
                
            except Exception:
                for client in entered_clients:
                    try:
                        client.__exit__(None, None, None)
                    except Exception as e:
                        logger.error(f"Error deactivating client: {e}")
                self.clients_activated = False
                raise
        else:
            yield self.clients
    
    def cleanup_servers(self):
        """Cleanup local server processes"""
        for process in self.server_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass

class SystemPromptLoader:
    """Handles system prompt loading and configuration with Bedrock caching"""
    
    @staticmethod
    def load_prompt() -> Dict[str, Any]:
        """Load system prompt with cache configuration"""
        try:
            output_path = Path.cwd() / "generated-diagrams"
            prompt = SYSTEM_INSTRUCTIONS + f"\n\nIMPORTANT: All generated files must be saved to: {output_path}"
            
            return {
                "system_prompt": prompt,
                "cache_config": {
                    "cache_control": {"type": "ephemeral"},
                    "cache_ttl": 3600
                }
            }
            
        except Exception as e:
            logger.error(f"Error loading context: {e}")
            output_path = Path.cwd() / "generated-diagrams"
            return {
                "system_prompt": f"You are an AWS architect assistant. Save all files to: {output_path}",
                "cache_config": {"cache_control": {"type": "ephemeral"}}
            }

class AWSArchitectAgent:
    """AWS Solution Architecture Agent using composition with Strands Agent
    
    Key Changes Made:
    - Removed inheritance - AWSArchitectAgent no longer extends Agent
    - Added composition - Uses self.agent = Agent(...) with MCP tools  
    - Simplified initialization - Tools passed directly to Agent constructor
    - Removed complex tool wrapping - GuidelineEnforcer class eliminated
    - Cleaner process_message - Delegates to self.agent(message)
    
    Benefits:
    - Simpler architecture - No complex inheritance or tool registration
    - Direct MCP integration - Tools work natively with Strands Agent
    - Reduced complexity - Eliminated 150+ lines of tool wrapping code
    - Better maintainability - Clear separation of concerns
    """
    
    def __init__(self):
        self.mcp_manager = MCPClientManager()
        self.agent = None  # Strands Agent instance (composition)
        self.mcp_tools = []  # Store loaded MCP tools
        self.initialized = False
        self.session_id = None  # Expose session ID
        # Rate limiter for LLM API calls - prevents exceeding service limits
        self.rate_limiter = RateLimiter(
            max_requests=RATE_LIMIT_MAX_REQUESTS, 
            time_window=RATE_LIMIT_TIME_WINDOW
        )
        
    def initialize(self) -> None:
        """Initialize the agent with MCP tools"""
        try:
            # Initialize MCP clients
            clients = self.mcp_manager.initialize_clients()
            if not clients:
                raise RuntimeError("Failed to initialize any MCP clients")
            
            # Load MCP tools directly from servers
            mcp_tools = self.mcp_manager.load_tools()
            
            # Add native file writing tool for deterministic output handling
            # This ensures files can be saved regardless of MCP server status
            native_tools = [write_file]
            all_tools = mcp_tools + native_tools
            
            if not all_tools:
                raise RuntimeError("No tools available")
            
            logger.info(f"Loaded {len(mcp_tools)} MCP tools + {len(native_tools)} native tools")
            
            # Load system prompt
            prompt_data = SystemPromptLoader.load_prompt()
            
            # Create session manager with random session ID
            # sessions_dir = Path(__file__).parent / "sessions"
            # sessions_dir.mkdir(exist_ok=True)
            # self.session_id = str(uuid.uuid4())
            # session_manager = FileSessionManager(
            #     session_id=self.session_id,
            #     storage_dir=str(sessions_dir)
            # )
            
            # Create Bedrock model instance with max_tokens configuration
            bedrock_model = BedrockModel(
                model_id=BEDROCK_MODEL_ID,
                max_tokens=MAX_TOKENS,
                additional_request_fields={"thinking": THINKING_CONFIG,
                                            "anthropic_beta":ANTHROPIC_BETA
                                           }
            )
            
            # Create Strands Agent with configured Bedrock model
            self.agent = Agent(
                name="aws-architect",
                system_prompt=prompt_data["system_prompt"],
                model=bedrock_model,
                tools=all_tools,
                trace_attributes={
                    # "session.id": self.session_id,
                }
            )
            
            self.initialized = True
            logger.info("Agent initialized successfully with MCP tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    


    
    def process_message(self, message: str, log_callback=None) -> Dict[str, Any]:
        """Process user message and return response with logs
        
        Uses composition pattern - delegates to self.agent(message)
        """
        if not self.initialized or not self.agent:
            return {"error": "Agent not initialized", "logs": "", "phase": "Error"}
        
        if not message or not message.strip():
            return {"error": "Empty message provided", "logs": "", "phase": "Error"}
        
        with LogCapture(stream_callback=log_callback).capture() as log_capture:
            try:
                logger.info(f"Processing user request: {message[:100]}...")
                
                # Use MCP client context manager for active connections
                with self.mcp_manager.active_clients():
                    # Delegate to Strands Agent with retry logic for Bedrock throttling
                    result = self._call_agent_with_retry(message.strip())
                
                phase = self._detect_current_phase(result.message, message)
                logger.info(f"Completed processing - Phase: {phase}")
                
                return {"result": result.message, "logs": log_capture.get_logs(), "phase": phase}
                
            except Exception as e:
                logger.error(f"Agent processing failed: {e}")
                return {
                    "error": f"Failed to process message: {str(e)}", 
                    "logs": log_capture.get_logs(),
                    "phase": "Error"
                }
    
    def _call_agent_with_retry(self, message: str, max_retries: int = 3):
        """
        Call agent with rate limiting and exponential backoff retry for Bedrock throttling
        
        Implements two-layer protection:
        1. Proactive rate limiting to prevent exceeding 5 requests/minute
        2. Reactive retry with exponential backoff for any throttling errors
        
        Args:
            message: User message to process
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            Agent response result
            
        Raises:
            Exception: Re-raises non-throttling exceptions or after max retries
        """
        for attempt in range(max_retries):
            try:
                # Proactive rate limiting - wait if needed to stay under 5/min limit
                self.rate_limiter.wait_if_needed()
                
                # Make LLM API call through Strands Agent
                return self.agent(message)
            except Exception as e:
                # Reactive handling - Check for Bedrock throttling errors
                if "throttlingException" in str(e) or "Too many requests" in str(e):
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2, 4, 8 seconds
                        wait_time = (2 ** attempt) * 2
                        logger.warning(f"Bedrock throttling detected, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                # Re-raise non-throttling exceptions or after max retries
                raise e
    
    def get_tool_info(self) -> List[Dict[str, str]]:
        """Get tool information for UI display using cached data from initialization"""
        if not self.initialized:
            return []
        
        tool_info = []
        
        # Use cached connection status and tools from initialization
        for config in self.mcp_manager.config:
            status = self.mcp_manager.connection_status.get(config.name, "🔴")
            # Extract only the emoji from status
            if "🟢" in status:
                status = "🟢"
            elif "🔴" in status:
                status = "🔴"
            tools = self.mcp_manager.server_tools.get(config.name, [])
            
            if tools:
                # Add entry for each tool
                for tool in tools:
                    tool_info.append({
                        "MCP Server": config.name,
                        "Status": status,
                        "Tool Name": getattr(tool, 'tool_name', str(tool))
                    })
            else:
                # Add single entry showing no tools available
                tool_info.append({
                    "MCP Server": config.name,
                    "Status": status,
                    "Tool Name": "No tools available"
                })
        
        return tool_info
    
    def get_model_info(self) -> str:
        """Get current model ID from the initialized agent"""
        if not self.initialized or not self.agent:
            return "Agent not initialized"
        
        # Try to get model from agent instance, fallback to config
        return getattr(self.agent, 'model', BEDROCK_MODEL_ID)
    
    def get_model_info(self) -> str:
        """Get current model ID for UI display"""
        return BEDROCK_MODEL_ID
    
    def _detect_current_phase(self, response_message, user_message: str) -> str:
        """
        Detect current phase using LLM-based intelligent classification
        Replaces keyword-based detection with context-aware analysis
        Added by: Vikrant
        """
        try:
            # Create phase classification prompt - Vikrant
            phase_prompt = f"""
            Analyze this conversation exchange and determine the current AWS architecture workflow phase.
            
            User Request: {user_message}
            Assistant Response: {str(response_message)[:500]}...
            
            Available Phases:
            1. Discovery Phase - Gathering business requirements, understanding needs, asking clarifying questions
            2. AWS Solution Architecture - Designing architecture, creating diagrams, selecting AWS services
            3. Cost Analysis - Calculating costs, pricing estimates, budget analysis
            4. AWS Well Architected Review - Reviewing against AWS best practices, assessing pillars
            
            Based on the content and intent, which phase is this conversation currently in?
            Respond with ONLY the exact phase name from the list above.
            """
            
            # Use LLM to intelligently classify phase - Vikrant
            phase_result = self.agent(phase_prompt.strip())
            detected_phase = self._parse_phase_from_response(str(phase_result.message))
            
            logger.info(f"LLM detected phase: {detected_phase}")
            return detected_phase
            
        except Exception as e:
            # Fallback to Discovery Phase on any error - Vikrant
            logger.warning(f"Phase detection failed, defaulting to Discovery: {e}")
            return "Discovery Phase"
    
    def _parse_phase_from_response(self, response: str) -> str:
        """
        Parse phase name from LLM response with fuzzy matching
        Added by: Vikrant
        """
        response_lower = response.lower().strip()
        
        # Define valid phases - Vikrant
        valid_phases = [
            "Discovery Phase",
            "AWS Solution Architecture", 
            "Cost Analysis",
            "AWS Well Architected Review"
        ]
        
        # Direct match check - Vikrant
        for phase in valid_phases:
            if phase.lower() in response_lower:
                return phase
        
        # Fuzzy matching for common variations - Vikrant
        if any(word in response_lower for word in ["discovery", "requirement", "gathering"]):
            return "Discovery Phase"
        elif any(word in response_lower for word in ["architecture", "design", "diagram"]):
            return "AWS Solution Architecture"
        elif any(word in response_lower for word in ["cost", "pricing", "budget"]):
            return "Cost Analysis"
        elif any(word in response_lower for word in ["well-architected", "review", "pillar"]):
            return "AWS Well Architected Review"
        
        # Default fallback - Vikrant
        return "Discovery Phase"
