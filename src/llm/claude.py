"""
Claude LLM client for the Schwab-AI Portfolio Manager.

This module provides a client for interacting with
Anthropic's Claude LLM API.
"""

import logging
import os
from typing import Dict, Any, List, Optional

import anthropic

from .client import BaseLLMClient, LLMClientError

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    """
    Client for Anthropic's Claude LLM API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Claude client.
        
        Args:
            config (dict): Configuration dictionary.
        """
        super().__init__(config)
        
        # Get API key from config or environment
        api_key = config.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise LLMClientError("Anthropic API key not found")
            
        # Create Claude client
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Set model (default to latest)
        self.model = config.get("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        
        logger.info(f"Initialized Claude client with model {self.model}")
    
    @property
    def name(self) -> str:
        """Return the name of the LLM provider."""
        return "Claude"
    
    def generate(self, prompt: str, 
                system_prompt: Optional[str] = None,
                temperature: float = 0.2,
                max_tokens: int = 2000) -> str:
        """
        Generate text using the Claude API.
        
        Args:
            prompt (str): The prompt text.
            system_prompt (str, optional): System instructions for Claude.
            temperature (float): Temperature parameter (0.0-1.0).
            max_tokens (int): Maximum tokens to generate.
            
        Returns:
            str: Generated text.
            
        Raises:
            LLMClientError: If text generation fails.
        """
        try:
            # Set default system prompt if not provided
            if system_prompt is None:
                system_prompt = (
                    "You are a financial analyst and investment advisor specializing in risk-averse "
                    "portfolio management. You will analyze market data, news, and portfolio information "
                    "to provide investment recommendations. Focus on capital preservation, risk management, "
                    "and stable returns while considering diversification, volatility, and fundamental analysis."
                )
            
            # Create message
            logger.debug(f"Generating text with Claude, prompt length: {len(prompt)}")
            
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract and return the generated text
            generated_text = response.content[0].text
            logger.debug(f"Generated {len(generated_text)} characters with Claude")
            
            return generated_text
            
        except Exception as e:
            error_msg = f"Claude text generation failed: {str(e)}"
            logger.error(error_msg)
            raise LLMClientError(error_msg) from e