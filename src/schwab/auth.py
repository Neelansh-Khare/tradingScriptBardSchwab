"""
Authentication module for Schwab API.

This module handles the authentication process for the Schwab API
using the schwab-py library.
"""

import logging
import os
import json
from pathlib import Path

from schwab import auth, client

logger = logging.getLogger(__name__)


class SchwabAuthError(Exception):
    """Exception raised for Schwab authentication errors."""
    pass


def authenticate_schwab(config):
    """
    Authenticate with the Schwab API using OAuth flow.
    
    Args:
        config (dict): Configuration dictionary containing Schwab credentials.
        
    Returns:
        SchwabClient: Authenticated Schwab client object.
        
    Raises:
        SchwabAuthError: If authentication fails.
    """
    try:
        # Extract credentials from config
        api_key = config.get("SCHWAB_API_KEY")
        app_secret = config.get("SCHWAB_APP_SECRET")
        callback_url = config.get("SCHWAB_CALLBACK_URL")
        token_path = config.get("SCHWAB_TOKEN_PATH")
        
        # Validate required configuration
        if not all([api_key, app_secret, callback_url, token_path]):
            missing = []
            if not api_key: missing.append("SCHWAB_API_KEY")
            if not app_secret: missing.append("SCHWAB_APP_SECRET")
            if not callback_url: missing.append("SCHWAB_CALLBACK_URL")
            if not token_path: missing.append("SCHWAB_TOKEN_PATH")
            
            raise SchwabAuthError(f"Missing required configuration: {', '.join(missing)}")
        
        # Create directory for token if it doesn't exist
        token_dir = os.path.dirname(token_path)
        if token_dir and not os.path.exists(token_dir):
            os.makedirs(token_dir)
        
        # Authenticate using schwab-py library
        logger.info("Authenticating with Schwab API...")
        schwab_client = auth.easy_client(
            api_key=api_key,
            app_secret=app_secret,
            callback_url=callback_url,
            token_path=token_path
        )
        
        # Test authentication by making a simple request
        logger.info("Testing authentication...")
        test_response = schwab_client.get_user_principals()
        test_response.raise_for_status()
        
        # Get user account information
        accounts_response = schwab_client.get_accounts()
        accounts_response.raise_for_status()
        accounts_data = accounts_response.json()
        
        # Log successful authentication
        account_ids = [acc.get('accountId') for acc in accounts_data.get('accounts', [])]
        logger.info(f"Successfully authenticated with {len(account_ids)} accounts")
        
        # Create our wrapped client
        from .client import SchwabClient
        return SchwabClient(schwab_client, accounts_data)
        
    except Exception as e:
        error_msg = f"Schwab authentication failed: {str(e)}"
        logger.error(error_msg)
        raise SchwabAuthError(error_msg) from e


def refresh_token(config):
    """
    Refresh the OAuth token if expired.
    
    Args:
        config (dict): Configuration dictionary containing Schwab credentials.
        
    Returns:
        bool: True if refresh was successful, False otherwise.
    """
    try:
        token_path = config.get("SCHWAB_TOKEN_PATH")
        
        # Load existing token
        with open(token_path, 'r') as f:
            token_data = json.load(f)
        
        # Refresh token
        api_key = config.get("SCHWAB_API_KEY")
        app_secret = config.get("SCHWAB_APP_SECRET")
        callback_url = config.get("SCHWAB_CALLBACK_URL")
        
        # Use refresh_token method from schwab-py
        new_token = auth.refresh_token(
            refresh_token=token_data.get('refresh_token'),
            api_key=api_key,
            app_secret=app_secret,
            callback_url=callback_url
        )
        
        # Save new token
        with open(token_path, 'w') as f:
            json.dump(new_token, f)
            
        logger.info("Successfully refreshed Schwab API token")
        return True
        
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        return False