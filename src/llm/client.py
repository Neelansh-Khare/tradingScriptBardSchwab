"""
LLM client interface for the Schwab-AI Portfolio Manager.

This module provides a common interface for interacting with
different LLM providers (OpenAI, Anthropic, etc.).
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    """Exception raised for LLM client errors."""
    pass


class BaseLLMClient(ABC):
    """
    Base abstract class for LLM clients.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM client."""
        self.config = config
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the LLM provider."""
        pass
        
    @abstractmethod
    def generate(self, prompt: str, 
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.2,
                 max_tokens: int = 2000) -> str:
        """
        Generate text using the LLM.
        
        Args:
            prompt (str): The prompt text.
            system_prompt (str, optional): System instructions for the LLM.
            temperature (float): Temperature parameter (0.0-1.0).
            max_tokens (int): Maximum tokens to generate.
            
        Returns:
            str: Generated text.
            
        Raises:
            LLMClientError: If text generation fails.
        """
        pass


def get_llm_client(config: Dict[str, Any]) -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        config (dict): Configuration dictionary.
        
    Returns:
        BaseLLMClient: An instance of the appropriate LLM client.
        
    Raises:
        LLMClientError: If no valid LLM client can be created.
    """
    # Check for OpenAI API key
    if config.get("OPENAI_API_KEY"):
        from .openai import OpenAIClient
        return OpenAIClient(config)
        
    # Check for Anthropic API key
    elif config.get("ANTHROPIC_API_KEY"):
        from .claude import ClaudeClient
        return ClaudeClient(config)
        
    # Check for Google Gemini API key
    elif config.get("GEMINI_API_KEY"):
        from .gemini import GeminiClient
        return GeminiClient(config)
        
    # Default to the first available
    else:
        error_msg = "No valid LLM API keys found in configuration"
        logger.error(error_msg)
        raise LLMClientError(error_msg)