"""
Tests for the Schwab authentication module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from src.schwab.auth import authenticate_schwab, refresh_token, SchwabAuthError


class TestSchwabAuth(unittest.TestCase):
    """Test cases for Schwab authentication."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample config for testing
        self.config = {
            "SCHWAB_API_KEY": "test_api_key",
            "SCHWAB_APP_SECRET": "test_app_secret",
            "SCHWAB_CALLBACK_URL": "https://localhost:8182/",
            "SCHWAB_TOKEN_PATH": "./tests/fixtures/test_token.json"
        }
        
    @patch('src.schwab.auth.auth.easy_client')
    def test_authenticate_schwab_success(self, mock_easy_client):
        """Test successful authentication."""
        # Mock the Schwab client
        mock_client = MagicMock()
        mock_easy_client.return_value = mock_client
        
        # Mock responses
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'accounts': [{'accountId': 'test_account_id'}]
        }
        mock_client.get_user_principals.return_value = mock_response
        mock_client.get_accounts.return_value = mock_response
        
        # Call authenticate_schwab
        with patch('src.schwab.auth.SchwabClient', MagicMock(return_value="mock_schwab_client")):
            result = authenticate_schwab(self.config)
            
        # Assert easy_client was called with correct args
        mock_easy_client.assert_called_once_with(
            api_key=self.config["SCHWAB_API_KEY"],
            app_secret=self.config["SCHWAB_APP_SECRET"],
            callback_url=self.config["SCHWAB_CALLBACK_URL"],
            token_path=self.config["SCHWAB_TOKEN_PATH"]
        )
        
        # Assert the client methods were called
        mock_client.get_user_principals.assert_called_once()
        mock_client.get_accounts.assert_called_once()
        
        # Assert the result is the mock client
        self.assertEqual(result, "mock_schwab_client")
        
    @patch('src.schwab.auth.auth.easy_client')
    def test_authenticate_schwab_missing_config(self, mock_easy_client):
        """Test authentication with missing config."""
        # Remove required config
        config = self.config.copy()
        del config["SCHWAB_API_KEY"]
        
        # Assert SchwabAuthError is raised
        with self.assertRaises(SchwabAuthError):
            authenticate_schwab(config)
        
        # Assert easy_client was not called
        mock_easy_client.assert_not_called()
        
    @patch('src.schwab.auth.auth.easy_client')
    def test_authenticate_schwab_api_error(self, mock_easy_client):
        """Test authentication with API error."""
        # Mock the Schwab client
        mock_client = MagicMock()
        mock_easy_client.return_value = mock_client
        
        # Mock error response
        mock_client.get_user_principals.side_effect = Exception("API Error")
        
        # Assert SchwabAuthError is raised
        with self.assertRaises(SchwabAuthError):
            authenticate_schwab(self.config)
        
    @patch('src.schwab.auth.auth.refresh_token')
    def test_refresh_token_success(self, mock_refresh_token):
        """Test successful token refresh."""
        # Set up test data
        token_data = {
            "access_token": "old_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600
        }
        new_token = {
            "access_token": "new_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }
        
        # Mock open and json load/dump
        with patch('builtins.open', unittest.mock.mock_open(read_data=str(token_data))), \
             patch('json.load', MagicMock(return_value=token_data)), \
             patch('json.dump', MagicMock()) as mock_json_dump:
            
            # Mock refresh_token
            mock_refresh_token.return_value = new_token
            
            # Call refresh_token
            result = refresh_token(self.config)
            
            # Assert success
            self.assertTrue(result)
            
            # Assert refresh_token was called with correct args
            mock_refresh_token.assert_called_once_with(
                refresh_token=token_data["refresh_token"],
                api_key=self.config["SCHWAB_API_KEY"],
                app_secret=self.config["SCHWAB_APP_SECRET"],
                callback_url=self.config["SCHWAB_CALLBACK_URL"]
            )
            
            # Assert json.dump was called with new token
            mock_json_dump.assert_called_once()
    
    @patch('src.schwab.auth.auth.refresh_token')
    def test_refresh_token_error(self, mock_refresh_token):
        """Test token refresh error."""
        # Set up test data
        token_data = {
            "access_token": "old_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600
        }
        
        # Mock open and json load
        with patch('builtins.open', unittest.mock.mock_open(read_data=str(token_data))), \
             patch('json.load', MagicMock(return_value=token_data)):
            
            # Mock refresh_token error
            mock_refresh_token.side_effect = Exception("Refresh Error")
            
            # Call refresh_token
            result = refresh_token(self.config)
            
            # Assert failure
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()