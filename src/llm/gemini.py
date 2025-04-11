"""
Google Gemini (formerly Bard) LLM client for the Schwab-AI Portfolio Manager.

This module provides a client for interacting with
Google's Gemini API.
"""

import logging
import os
from typing import Dict, Any, List, Optional

import google.generativeai as genai

from .client import BaseLLMClient, LLMClientError

logger = logging.getLogger(__name__)


class GeminiClient(BaseLLMClient):
    """
    Client for Google's Gemini API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Gemini client.
        
        Args:
            config (dict): Configuration dictionary.
        """
        super().__init__(config)
        
        # Get API key from config or environment
        api_key = config.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            raise LLMClientError("Google Gemini API key not found")
            
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Set model (default to latest)
        self.model_name = config.get("GEMINI_MODEL", "gemini-pro")
        
        # Get the model
        try:
            available_models = [m.name for m in genai.list_models()]
            model_full_name = next((m for m in available_models if self.model_name in m), None)
            
            if not model_full_name:
                logger.warning(f"Model {self.model_name} not found, using default model")
                # Use the first available text model
                model_full_name = next((m for m in available_models if "text" in genai.get_model(m).supported_generation_methods), None)
                
            self.model = genai.GenerativeModel(model_full_name or self.model_name)
            logger.info(f"Initialized Gemini client with model {self.model_name}")
        except Exception as e:
            error_msg = f"Failed to initialize Gemini client: {str(e)}"
            logger.error(error_msg)
            raise LLMClientError(error_msg) from e
    
    @property
    def name(self) -> str:
        """Return the name of the LLM provider."""
        return "Gemini"
    
    def generate(self, prompt: str, 
                system_prompt: Optional[str] = None,
                temperature: float = 0.2,
                max_tokens: int = 2000) -> str:
        """
        Generate text using the Gemini API.
        
        Args:
            prompt (str): The prompt text.
            system_prompt (str, optional): System instructions for Gemini.
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
            
            # Create combined prompt with system instructions
            combined_prompt = f"{system_prompt}\n\n{prompt}"
            
            logger.debug(f"Generating text with Gemini, prompt length: {len(combined_prompt)}")
            
            # Generate content with retry logic
            try:
                # Call Gemini API
                response = self.model.generate_content(
                    combined_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                        top_p=0.95,
                        top_k=40,
                    ),
                )
                
                # Extract and return the generated text
                generated_text = response.text
                logger.debug(f"Generated {len(generated_text)} characters with Gemini")
                
                return generated_text
                
            except Exception as e:
                error_msg = f"Gemini generation failed: {str(e)}"
                logger.error(error_msg)
                
                # Try one more time with a simpler prompt if the first attempt failed
                try:
                    response = self.model.generate_content(
                        prompt,  # Just use the main prompt without system instructions
                        generation_config=genai.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                            top_p=0.95,
                            top_k=40,
                        ),
                    )
                    
                    generated_text = response.text
                    logger.debug(f"Generated {len(generated_text)} characters with Gemini (fallback)")
                    
                    return generated_text
                except Exception as retry_error:
                    raise LLMClientError(f"Gemini retry also failed: {str(retry_error)}") from retry_error
                
        except Exception as e:
            error_msg = f"Gemini text generation failed: {str(e)}"
            logger.error(error_msg)
            raise LLMClientError(error_msg) from e