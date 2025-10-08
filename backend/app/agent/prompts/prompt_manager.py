"""
Prompt management system for loading and injecting mode-specific prompts.
"""
import os
import re
from pathlib import Path
from typing import Dict, Optional, Any
import yaml
from datetime import datetime
import logging

from app.core.datetime_utils import utc_now, to_utc_iso8601

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompt templates for different conversation modes."""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize the prompt manager.
        
        Args:
            prompts_dir: Directory containing prompt templates
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent
        self.prompts_dir = prompts_dir
        self._cache: Dict[str, str] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        
    def load_prompt(self, mode: str, version: str = "v001") -> str:
        """
        Load a prompt template for the specified mode.
        
        Args:
            mode: Conversation mode (green, blue, indigo, violet)
            version: Prompt version (default: v001)
            
        Returns:
            Prompt content as string
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If prompt file is invalid
        """
        cache_key = f"{mode}_{version}"
        
        # Check cache first
        if cache_key in self._cache:
            logger.debug(f"Returning cached prompt for {mode} {version}")
            return self._cache[cache_key]
        
        # Load from file
        file_path = self.prompts_dir / f"{mode}_{version}.md"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse and cache
            metadata, prompt_body = self._parse_prompt_file(content)
            self._cache[cache_key] = prompt_body
            self._metadata_cache[cache_key] = metadata
            
            logger.info(f"Loaded prompt for {mode} {version}")
            return prompt_body
            
        except Exception as e:
            logger.error(f"Error loading prompt {file_path}: {e}")
            raise ValueError(f"Invalid prompt file: {e}")
    
    def _parse_prompt_file(self, content: str) -> tuple[Dict[str, Any], str]:
        """
        Parse prompt file to extract metadata and body.
        
        Args:
            content: Raw file content
            
        Returns:
            Tuple of (metadata dict, prompt body)
        """
        # Split on the YAML front matter delimiter
        parts = content.split('---', 2)
        
        if len(parts) >= 3:
            # Has YAML front matter
            try:
                metadata = yaml.safe_load(parts[1])
                prompt_body = parts[2].strip()
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML front matter: {e}")
                metadata = {}
                prompt_body = content
        else:
            # No front matter
            metadata = {}
            prompt_body = content.strip()
        
        return metadata, prompt_body
    
    def get_system_prompt(self, mode: str, user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get complete system prompt with common instructions and mode-specific prompt.
        
        Args:
            mode: Conversation mode
            user_context: Optional context to inject into prompt
            
        Returns:
            Complete system prompt
        """
        # Load common instructions
        try:
            common_path = self.prompts_dir / "common_instructions.md"
            with open(common_path, 'r', encoding='utf-8') as f:
                common_instructions = f.read()
        except FileNotFoundError:
            logger.warning("Common instructions not found, using mode prompt only")
            common_instructions = ""
        
        # Load mode-specific prompt
        mode_prompt = self.load_prompt(mode)
        
        # Combine prompts
        full_prompt = f"{common_instructions}\n\n---\n\n{mode_prompt}"
        
        # Inject context if provided
        if user_context:
            full_prompt = self.inject_variables(full_prompt, user_context)
        
        return full_prompt
    
    def inject_variables(self, prompt: str, variables: Dict[str, Any]) -> str:
        """
        Inject variables into prompt template.

        Args:
            prompt: Prompt template with {variable} placeholders
            variables: Dictionary of variables to inject

        Returns:
            Prompt with variables replaced
        """
        # Add standard variables
        variables = {
            **variables,
            'current_time': to_utc_iso8601(utc_now()),
            'model': 'gpt-5-2025-08-07',
        }

        # Replace variables in prompt
        for key, value in variables.items():
            placeholder = f"{{{key}}}"

            # Special handling for holdings array
            if key == 'holdings' and isinstance(value, list):
                if value:
                    holdings_text = "Recent Portfolio Holdings (Top 50):\n"
                    for holding in value:
                        symbol = holding.get('symbol', 'N/A')
                        quantity = holding.get('quantity', 0)
                        market_value = holding.get('market_value', 0)
                        position_type = holding.get('position_type', 'LONG')
                        holdings_text += f"- {symbol}: {quantity} shares, ${market_value:,.2f} ({position_type})\n"
                    prompt = prompt.replace(placeholder, holdings_text)
                else:
                    prompt = prompt.replace(placeholder, "No holdings data available")
            elif value is None:
                # Handle None values
                prompt = prompt.replace(placeholder, "N/A")
            else:
                # Default string conversion
                prompt = prompt.replace(placeholder, str(value))

        return prompt
    
    def get_metadata(self, mode: str, version: str = "v001") -> Dict[str, Any]:
        """
        Get metadata for a prompt.
        
        Args:
            mode: Conversation mode
            version: Prompt version
            
        Returns:
            Metadata dictionary
        """
        cache_key = f"{mode}_{version}"
        
        # Load if not cached
        if cache_key not in self._metadata_cache:
            self.load_prompt(mode, version)
        
        return self._metadata_cache.get(cache_key, {})
    
    def get_token_budget(self, mode: str) -> int:
        """
        Get token budget for a mode.
        
        Args:
            mode: Conversation mode
            
        Returns:
            Token budget (default: 2000)
        """
        metadata = self.get_metadata(mode)
        return metadata.get('token_budget', 2000)
    
    def list_available_modes(self) -> list[str]:
        """
        List all available conversation modes.
        
        Returns:
            List of mode names
        """
        modes = set()
        
        # Scan prompts directory for mode files
        for file_path in self.prompts_dir.glob("*_v*.md"):
            # Extract mode from filename (e.g., green_v001.md -> green)
            match = re.match(r'^([a-z]+)_v\d+\.md$', file_path.name)
            if match:
                modes.add(match.group(1))
        
        return sorted(list(modes))
    
    def validate_mode(self, mode: str) -> bool:
        """
        Check if a mode is valid and available.
        
        Args:
            mode: Mode name to validate
            
        Returns:
            True if mode is available
        """
        return mode in self.list_available_modes()
    
    def format_mode_info(self, mode: str) -> str:
        """
        Get formatted information about a mode.
        
        Args:
            mode: Conversation mode
            
        Returns:
            Formatted mode description
        """
        metadata = self.get_metadata(mode)
        
        info = f"Mode: {mode.capitalize()}\n"
        info += f"Persona: {metadata.get('persona', 'Standard analyst')}\n"
        info += f"Token Budget: {metadata.get('token_budget', 2000)}\n"
        
        return info


# Singleton instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get or create the singleton prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager