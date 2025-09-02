"""
OpenAI Provider Implementation
Implements OpenAI-specific ID transformations and formats
Part of Phase 10.3: Multi-LLM Support Foundation
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import uuid
from app.utils.llm_provider_base import LLMProviderBase


class OpenAIProvider(LLMProviderBase):
    """
    OpenAI-specific implementation of LLM provider interface.
    Handles OpenAI's ID formats and message structures.
    """
    
    def __init__(self):
        """Initialize OpenAI provider."""
        super().__init__("openai")
    
    # ==================== ID Generation Methods ====================
    
    def generate_provider_tool_call_id(self) -> str:
        """
        Generate an OpenAI-compatible tool call ID.
        Format: call_{24 character hex string}
        
        Returns:
            OpenAI-format tool call ID
        """
        return f"call_{uuid.uuid4().hex[:24]}"
    
    # ==================== Tool Call Format Methods ====================
    
    def format_tool_call(self, 
                        tool_name: str, 
                        tool_args: Dict[str, Any],
                        tool_call_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a tool call in OpenAI's expected format.
        
        Args:
            tool_name: Name of the tool/function
            tool_args: Arguments for the tool
            tool_call_id: Optional ID (will generate if not provided)
            
        Returns:
            OpenAI-format tool call dictionary
        """
        if not tool_call_id:
            tool_call_id = self.generate_provider_tool_call_id()
        
        return {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(tool_args) if isinstance(tool_args, dict) else tool_args
            }
        }
    
    def parse_tool_response(self, response: Dict[str, Any]) -> Tuple[str, Any]:
        """
        Parse a tool response from OpenAI format.
        
        Args:
            response: OpenAI tool response
            
        Returns:
            Tuple of (tool_call_id, result)
        """
        tool_call_id = response.get("tool_call_id", "")
        result = response.get("result", response.get("content", ""))
        
        return tool_call_id, result
    
    # ==================== Message Format Methods ====================
    
    def format_message(self, 
                      role: str, 
                      content: str,
                      message_id: Optional[str] = None,
                      tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Format a message in OpenAI's expected format.
        
        Args:
            role: Message role (user/assistant/system)
            content: Message content
            message_id: Optional message ID (not used by OpenAI API directly)
            tool_calls: Optional list of tool calls
            
        Returns:
            OpenAI-format message dictionary
        """
        message = {
            "role": role,
            "content": content
        }
        
        # Add tool calls if present (only for assistant messages)
        if tool_calls and role == "assistant":
            message["tool_calls"] = tool_calls
        
        # Store our message ID in metadata (not sent to OpenAI)
        if message_id:
            message["_internal_id"] = message_id
        
        return message
    
    def parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a message from OpenAI format to universal format.
        
        Args:
            message: OpenAI message format
            
        Returns:
            Universal message format
        """
        universal_message = {
            "role": message.get("role", "assistant"),
            "content": message.get("content", ""),
            "id": message.get("_internal_id") or self.generate_universal_message_id(),
            "tool_calls": None
        }
        
        # Handle tool calls if present
        if "tool_calls" in message:
            tool_calls = []
            for tc in message["tool_calls"]:
                # Ensure proper format
                if not tc.get("id"):
                    tc["id"] = self.generate_provider_tool_call_id()
                tool_calls.append(tc)
            universal_message["tool_calls"] = tool_calls
        
        return universal_message
    
    # ==================== Streaming Event Methods ====================
    
    def format_sse_event(self, 
                        event_type: str, 
                        data: Dict[str, Any],
                        run_id: str,
                        sequence: int) -> str:
        """
        Format an SSE event for OpenAI streaming.
        
        Args:
            event_type: Type of event (token, tool_call, error, done, etc.)
            data: Event data
            run_id: Run/session identifier
            sequence: Sequence number for ordering
            
        Returns:
            Formatted SSE event string
        """
        # Map our event types to what frontend expects
        event_mapping = {
            "token": "token",
            "tool_call": "tool_call",
            "tool_result": "tool_result",
            "error": "error",
            "done": "done",
            "heartbeat": "heartbeat",
            "message_created": "message_created"
        }
        
        mapped_event = event_mapping.get(event_type, event_type)
        
        # Build event data
        event_data = {
            "run_id": run_id,
            "seq": sequence,
            "type": mapped_event,
            "data": data,
            "timestamp": int(uuid.uuid4().time * 1000)  # Timestamp in milliseconds
        }
        
        # Format as SSE
        return f"event: {mapped_event}\ndata: {json.dumps(event_data)}\n\n"
    
    # ==================== Validation Methods ====================
    
    def validate_tool_call_id(self, tool_call_id: str) -> bool:
        """
        Validate if a tool call ID matches OpenAI's format.
        Expected format: call_{24 character hex string}
        
        Args:
            tool_call_id: ID to validate
            
        Returns:
            True if valid OpenAI format, False otherwise
        """
        if not tool_call_id or not isinstance(tool_call_id, str):
            return False
        
        # Check format: call_XXXXXXXXXXXXXXXXXXXXXXXX (call_ + 24 hex chars)
        if not tool_call_id.startswith("call_"):
            return False
        
        hex_part = tool_call_id[5:]  # Remove "call_" prefix
        if len(hex_part) != 24:
            return False
        
        # Check if all characters are valid hex
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False
    
    # ==================== ID Format Info ====================
    
    def get_id_format_info(self) -> Dict[str, str]:
        """
        Get information about OpenAI's ID formats.
        
        Returns:
            Dictionary describing OpenAI ID formats
        """
        return {
            "tool_call": "call_{24_hex_chars}",
            "message": "UUID (internal only)",
            "conversation": "UUID (internal only)",
            "run": "run_{12_hex_chars}",
            "example_tool_call": self.generate_provider_tool_call_id()
        }
    
    # ==================== Backward Compatibility Methods ====================
    
    def fix_malformed_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix malformed tool calls from legacy conversations.
        Ensures backward compatibility with existing data.
        
        Args:
            tool_call: Potentially malformed tool call
            
        Returns:
            Properly formatted tool call
        """
        # If it's already properly formatted, return as-is
        if (tool_call.get("id") and 
            tool_call.get("type") == "function" and 
            "function" in tool_call):
            return tool_call
        
        # Fix missing or malformed structure
        fixed_call = {
            "id": tool_call.get("id") or self.generate_provider_tool_call_id(),
            "type": "function",
            "function": {}
        }
        
        # Handle different legacy formats
        if "function" in tool_call:
            fixed_call["function"] = tool_call["function"]
        else:
            # Assume flat structure with name and args
            fixed_call["function"] = {
                "name": tool_call.get("name", tool_call.get("tool_name", "unknown")),
                "arguments": json.dumps(tool_call.get("args", tool_call.get("tool_args", {})))
            }
        
        return fixed_call
    
    def ensure_tool_call_ids(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure all tool calls have valid IDs.
        Fixes missing IDs for backward compatibility.
        
        Args:
            tool_calls: List of tool calls
            
        Returns:
            List of tool calls with guaranteed IDs
        """
        if not tool_calls:
            return []
        
        fixed_calls = []
        for tc in tool_calls:
            fixed_call = self.fix_malformed_tool_call(tc)
            fixed_calls.append(fixed_call)
        
        return fixed_calls