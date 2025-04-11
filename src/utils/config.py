"""
Configuration utilities for the Schwab-AI Portfolio Manager.

This module handles loading and validating configuration.
"""

import os
import logging
from typing import Dict, Any
from pathlib import Path
import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a file or environment variables.
    
    Args:
        config_path (str): Path to the configuration file.
        
    Returns:
        Dict[str, Any]: Configuration dictionary.
        
    Raises:
        ConfigError: If configuration loading fails.
    """
    config = {}
    
    try:
        # Determine file type
        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
            config = _load_yaml_config(config_path)
        elif config_path.endswith('.env'):
            config = _load_env_config(config_path)
        else:
            # Try both methods
            if os.path.exists(config_path):
                try:
                    config = _load_yaml_config(config_path)
                except Exception:
                    config = _load_env_config(config_path)
            else:
                raise ConfigError(f"Configuration file not found: {config_path}")
                
        # Validate required configuration
        validate_config(config)
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
        
    except Exception as e:
        error_msg = f"Failed to load configuration: {str(e)}"
        logger.error(error_msg)
        raise ConfigError(error_msg) from e


def _load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path (str): Path to the YAML configuration file.
        
    Returns:
        Dict[str, Any]: Configuration dictionary.
        
    Raises:
        ConfigError: If YAML file loading fails.
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        if not isinstance(config, dict):
            raise ConfigError(f"Invalid YAML configuration format in {config_path}")
            
        return config
        
    except Exception as e:
        error_msg = f"Failed to load YAML configuration: {str(e)}"
        logger.error(error_msg)
        raise ConfigError(error_msg) from e


def _load_env_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a .env file or environment variables.
    
    Args:
        config_path (str): Path to the .env file.
        
    Returns:
        Dict[str, Any]: Configuration dictionary.
        
    Raises:
        ConfigError: If .env file loading fails.
    """
    try:
        # Load .env file if it exists
        if os.path.exists(config_path):
            load_dotenv(config_path)
        
        # Get all environment variables
        config = {}
        
        # Schwab API credentials
        config["SCHWAB_API_KEY"] = os.environ.get("SCHWAB_API_KEY")
        config["SCHWAB_APP_SECRET"] = os.environ.get("SCHWAB_APP_SECRET")
        config["SCHWAB_CALLBACK_URL"] = os.environ.get("SCHWAB_CALLBACK_URL")
        config["SCHWAB_TOKEN_PATH"] = os.environ.get("SCHWAB_TOKEN_PATH")
        config["SCHWAB_ACCOUNT_ID"] = os.environ.get("SCHWAB_ACCOUNT_ID")
        
        # LLM API credentials
        config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
        config["OPENAI_MODEL"] = os.environ.get("OPENAI_MODEL", "gpt-4")
        config["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY")
        config["ANTHROPIC_MODEL"] = os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        
        # Risk profile settings
        if "RISK_TOLERANCE" in os.environ:
            config["RISK_TOLERANCE"] = int(os.environ.get("RISK_TOLERANCE", "5"))
        if "MAX_POSITION_SIZE_PERCENT" in os.environ:
            config["MAX_POSITION_SIZE_PERCENT"] = float(os.environ.get("MAX_POSITION_SIZE_PERCENT", "10"))
        if "MAX_SECTOR_EXPOSURE_PERCENT" in os.environ:
            config["MAX_SECTOR_EXPOSURE_PERCENT"] = float(os.environ.get("MAX_SECTOR_EXPOSURE_PERCENT", "25"))
        
        # Trading parameters
        if "ENABLE_AUTO_TRADING" in os.environ:
            config["ENABLE_AUTO_TRADING"] = os.environ.get("ENABLE_AUTO_TRADING").lower() == "true"
        if "DRY_RUN" in os.environ:
            config["DRY_RUN"] = os.environ.get("DRY_RUN").lower() == "true"
        if "MAX_TRADES_PER_SESSION" in os.environ:
            config["MAX_TRADES_PER_SESSION"] = int(os.environ.get("MAX_TRADES_PER_SESSION", "5"))
        if "MIN_CASH_RESERVE_PERCENT" in os.environ:
            config["MIN_CASH_RESERVE_PERCENT"] = float(os.environ.get("MIN_CASH_RESERVE_PERCENT", "5"))
            
        return config
        
    except Exception as e:
        error_msg = f"Failed to load .env configuration: {str(e)}"
        logger.error(error_msg)
        raise ConfigError(error_msg) from e


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration.
    
    Args:
        config (Dict[str, Any]): Configuration dictionary.
        
    Raises:
        ConfigError: If configuration is invalid.
    """
    # Check for required Schwab API credentials
    required_schwab_keys = ["SCHWAB_API_KEY", "SCHWAB_APP_SECRET", "SCHWAB_CALLBACK_URL", "SCHWAB_TOKEN_PATH"]
    missing_keys = [key for key in required_schwab_keys if not config.get(key)]
    
    if missing_keys:
        raise ConfigError(f"Missing required Schwab API configuration: {', '.join(missing_keys)}")
    
    # Check for at least one LLM API key
    if not config.get("OPENAI_API_KEY") and not config.get("ANTHROPIC_API_KEY"):
        raise ConfigError("At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY is required")
    
    # Set default values for missing optional settings
    config.setdefault("RISK_TOLERANCE", 5)
    config.setdefault("MAX_POSITION_SIZE_PERCENT", 10.0)
    config.setdefault("MAX_SECTOR_EXPOSURE_PERCENT", 25.0)
    config.setdefault("ENABLE_AUTO_TRADING", False)
    config.setdefault("DRY_RUN", True)
    config.setdefault("MAX_TRADES_PER_SESSION", 5)
    config.setdefault("MIN_CASH_RESERVE_PERCENT", 5.0)
    
    # Validate numeric values
    if not 1 <= config["RISK_TOLERANCE"] <= 10:
        raise ConfigError(f"RISK_TOLERANCE must be between 1 and 10, got {config['RISK_TOLERANCE']}")
        
    if not 0 < config["MAX_POSITION_SIZE_PERCENT"] <= 100:
        raise ConfigError(f"MAX_POSITION_SIZE_PERCENT must be between 0 and 100, got {config['MAX_POSITION_SIZE_PERCENT']}")
        
    if not 0 < config["MAX_SECTOR_EXPOSURE_PERCENT"] <= 100:
        raise ConfigError(f"MAX_SECTOR_EXPOSURE_PERCENT must be between 0 and 100, got {config['MAX_SECTOR_EXPOSURE_PERCENT']}")