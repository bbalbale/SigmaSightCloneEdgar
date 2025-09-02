"""
LLM Provider Base Class
Provides abstract interface for multi-LLM support
Part of Phase 10.3: Multi-LLM Support Foundation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
from datetime import datetime
import json


class LLMProviderBase(ABC):
    """
    Abstract base class for LLM provider implementations.
    Defines universal interface for ID generation and transformation.
    """
    
    def __init__(self, provider_name: str):
        """
        Initialize the provider base.
        
        Args:
            provider_name: Unique identifier for this provider (e.g., 'openai', 'anthropic')
        """
        self.provider_name = provider_name
        self._id_mapping: Dict[str, str] = {}  # Universal ID -> Provider ID mapping
    
    # ==================== ID Generation Methods ====================
    
    def generate_universal_message_id(self) -> str:
        """
        Generate a universal message ID that's provider-agnostic.
        This is the primary ID used by our backend.
        
        Returns:
            UUID string for message identification
        """
        return str(uuid4())
    
    def generate_universal_conversation_id(self) -> str:
        """
        Generate a universal conversation ID.
        
        Returns:
            UUID string for conversation identification
        """
        return str(uuid4())
    
    def generate_universal_run_id(self) -> str:
        """
        Generate a universal run ID for streaming sessions.
        
        Returns:
            String identifier for run/streaming session
        """
        return f"run_{uuid4().hex[:12]}"
    
    @abstractmethod
    def generate_provider_tool_call_id(self) -> str:
        """
        Generate a provider-specific tool call ID.
        Must be implemented by each provider.
        
        Returns:
            Provider-specific tool call ID format
        """
        pass
    
    # ==================== ID Transformation Methods ====================
    
    def map_universal_to_provider(self, universal_id: str, provider_id: str) -> None:
        """
        Store mapping between universal ID and provider-specific ID.
        
        Args:
            universal_id: Our backend UUID
            provider_id: Provider's specific ID format
        """
        self._id_mapping[universal_id] = provider_id
    
    def get_provider_id(self, universal_id: str) -> Optional[str]:
        """
        Retrieve provider ID for a given universal ID.
        
        Args:
            universal_id: Our backend UUID
            
        Returns:
            Provider-specific ID if mapped, None otherwise
        """
        return self._id_mapping.get(universal_id)
    
    def get_universal_id(self, provider_id: str) -> Optional[str]:
        """
        Reverse lookup: get universal ID from provider ID.
        
        Args:
            provider_id: Provider-specific ID
            
        Returns:
            Universal ID if found, None otherwise
        """
        for universal, provider in self._id_mapping.items():
            if provider == provider_id:
                return universal
        return None
    
    # ==================== Tool Call Format Methods ====================
    
    @abstractmethod
    def format_tool_call(self, 
                        tool_name: str, 
                        tool_args: Dict[str, Any],
                        tool_call_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a tool call in provider-specific format.
        Must be implemented by each provider.
        
        Args:
            tool_name: Name of the tool/function to call
            tool_args: Arguments for the tool
            tool_call_id: Optional ID (will generate if not provided)
            
        Returns:
            Provider-specific tool call format
        """
        pass
    
    @abstractmethod
    def parse_tool_response(self, response: Dict[str, Any]) -> Tuple[str, Any]:
        """
        Parse a tool response from provider format.
        Must be implemented by each provider.
        
        Args:
            response: Provider-specific tool response
            
        Returns:
            Tuple of (tool_call_id, result)
        """
        pass
    
    # ==================== Message Format Methods ====================
    
    @abstractmethod
    def format_message(self, 
                      role: str, 
                      content: str,
                      message_id: Optional[str] = None,
                      tool_calls: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Format a message in provider-specific format.
        Must be implemented by each provider.
        
        Args:
            role: Message role (user/assistant/system)
            content: Message content
            message_id: Optional message ID
            tool_calls: Optional list of tool calls
            
        Returns:
            Provider-specific message format
        """
        pass
    
    @abstractmethod
    def parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a message from provider format to universal format.
        Must be implemented by each provider.
        
        Args:
            message: Provider-specific message format
            
        Returns:
            Universal message format with role, content, id, tool_calls
        """
        pass
    
    # ==================== Streaming Event Methods ====================
    
    @abstractmethod
    def format_sse_event(self, 
                        event_type: str, 
                        data: Dict[str, Any],
                        run_id: str,
                        sequence: int) -> str:
        """
        Format an SSE event for streaming.
        Must be implemented by each provider.
        
        Args:
            event_type: Type of event (token, tool_call, error, done, etc.)
            data: Event data
            run_id: Run/session identifier
            sequence: Sequence number for ordering
            
        Returns:
            Formatted SSE event string
        """
        pass
    
    # ==================== Validation Methods ====================
    
    def validate_tool_call_id(self, tool_call_id: str) -> bool:
        """
        Validate if a tool call ID matches provider's expected format.
        Can be overridden by specific providers.
        
        Args:
            tool_call_id: ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Default validation - non-empty string
        return bool(tool_call_id and isinstance(tool_call_id, str))
    
    def validate_message_id(self, message_id: str) -> bool:
        """
        Validate if a message ID is a valid UUID.
        
        Args:
            message_id: ID to validate
            
        Returns:
            True if valid UUID, False otherwise
        """
        try:
            # Try to parse as UUID
            from uuid import UUID
            UUID(message_id)
            return True
        except (ValueError, AttributeError):
            return False
    
    # ==================== Error Handling Methods ====================
    
    def handle_missing_id(self, 
                         id_type: str, 
                         context: Dict[str, Any]) -> str:
        """
        Handle cases where an ID is missing.
        Generates appropriate ID based on type.
        
        Args:
            id_type: Type of ID needed (message, tool_call, etc.)
            context: Additional context for ID generation
            
        Returns:
            Generated ID
        """
        if id_type == "message":
            return self.generate_universal_message_id()
        elif id_type == "tool_call":
            return self.generate_provider_tool_call_id()
        elif id_type == "conversation":
            return self.generate_universal_conversation_id()
        elif id_type == "run":
            return self.generate_universal_run_id()
        else:
            # Fallback to UUID
            return str(uuid4())
    
    # ==================== Metadata Methods ====================
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.
        
        Returns:
            Dictionary with provider metadata
        """
        return {
            "name": self.provider_name,
            "supports_streaming": True,
            "supports_tools": True,
            "id_format": self.get_id_format_info(),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    @abstractmethod
    def get_id_format_info(self) -> Dict[str, str]:
        """
        Get information about ID formats used by this provider.
        Must be implemented by each provider.
        
        Returns:
            Dictionary describing ID formats
        """
        pass
    
    # ==================== Utility Methods ====================
    
    def clear_id_mappings(self) -> None:
        """Clear all stored ID mappings."""
        self._id_mapping.clear()
    
    def get_mapping_count(self) -> int:
        """Get count of stored ID mappings."""
        return len(self._id_mapping)
    
    def export_mappings(self) -> str:
        """Export ID mappings as JSON string."""
        return json.dumps(self._id_mapping, indent=2)
    
    def import_mappings(self, mappings_json: str) -> None:
        """Import ID mappings from JSON string."""
        self._id_mapping = json.loads(mappings_json)