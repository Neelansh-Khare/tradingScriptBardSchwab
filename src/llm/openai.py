"""
OpenAI LLM client for the Schwab-AI Portfolio Manager.

This module provides a client for interacting with
OpenAI's GPT API.
"""

import logging
import os
from typing import Dict, Any, List, Optional

import openai

from .client import BaseLLMClient, LLMClientError

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """
    Client for OpenAI's GPT API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the OpenAI client.
        
        Args:
            config (dict): Configuration dictionary.
        """
        super().__init__(config)
        
        # Get API key from config or environment
        api_key = config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            raise LLMClientError("OpenAI API key not found")
            
        # Create OpenAI client
        self.client = openai.OpenAI(api_key=api_key)
        
        # Set model (default to latest)
        self.model = config.get("OPENAI_MODEL", "gpt-4")
        
        logger.info(f"Initialized OpenAI client with model {self.model}")
    
    @property
    def name(self) -> str:
        """Return the name of the LLM provider."""
        return "OpenAI"
    
    def generate(self, prompt: str, 
                system_prompt: Optional[str] = None,
                temperature: float = 0.2,
                max_tokens: int = 2000) -> str:
        """
        Generate text using the OpenAI API.
        
        Args:
            prompt (str): The prompt text.
            system_prompt (str, optional): System instructions for GPT.
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
            logger.debug(f"Generating text with OpenAI, prompt length: {len(prompt)}")
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Extract and return the generated text
            generated_text = response.choices[0].message.content
            logger.debug(f"Generated {len(generated_text)} characters with OpenAI")
            
            return generated_text
            
        except Exception as e:
            error_msg = f"OpenAI text generation failed: {str(e)}"
            logger.error(error_msg)
            raise LLMClientError(error_msg) from e