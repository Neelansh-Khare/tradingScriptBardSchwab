"""
Schwab API client wrapper.

This module provides a wrapper around the schwab-py client
to simplify interactions with the Schwab API.
"""

import logging
import json
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class SchwabClientError(Exception):
    """Exception raised for Schwab client errors."""
    pass


class SchwabClient:
    """
    Wrapper around the schwab-py client to simplify interactions.
    """
    
    def __init__(self, schwab_client, accounts_data):
        """
        Initialize the Schwab client wrapper.
        
        Args:
            schwab_client: The authenticated schwab-py client.
            accounts_data (dict): Account information from get_accounts.
        """
        self.client = schwab_client
        self.accounts = accounts_data.get('accounts', [])
        self.account_ids = [acc.get('accountId') for acc in self.accounts]
        self.primary_account_id = self.account_ids[0] if self.account_ids else None
        
        logger.info(f"Initialized SchwabClient with {len(self.account_ids)} accounts")
    
    def get_portfolio(self, account_id=None):
        """
        Get the portfolio for the specified account.
        
        Args:
            account_id (str, optional): The account ID to retrieve. If None,
                                       uses the primary account.
                                       
        Returns:
            Portfolio: A Portfolio object containing the positions.
            
        Raises:
            SchwabClientError: If the request fails.
        """
        try:
            # Use primary account if none specified
            if account_id is None:
                account_id = self.primary_account_id
                
            if not account_id:
                raise SchwabClientError("No account ID available")
            
            # Get positions for the account
            response = self.client.get_account(
                account_id=account_id,
                fields=['positions']
            )
            response.raise_for_status()
            account_data = response.json()
            
            # Create Portfolio object
            from .portfolio import Portfolio, Position
            
            # Extract positions data
            positions_data = account_data.get('securitiesAccount', {}).get('positions', [])
            positions = []
            
            for pos_data in positions_data:
                instrument = pos_data.get('instrument', {})
                position = Position(
                    symbol=instrument.get('symbol'),
                    quantity=pos_data.get('longQuantity', 0) - pos_data.get('shortQuantity', 0),
                    asset_type=instrument.get('assetType'),
                    cost_basis=pos_data.get('averagePrice', 0),
                    market_value=pos_data.get('marketValue', 0),
                    current_price=pos_data.get('marketPrice', 0),
                    instrument_data=instrument
                )
                positions.append(position)
            
            # Create portfolio
            portfolio = Portfolio(
                account_id=account_id,
                positions=positions,
                account_value=account_data.get('securitiesAccount', {}).get('currentBalances', {}).get('liquidationValue', 0),
                cash_balance=account_data.get('securitiesAccount', {}).get('currentBalances', {}).get('cashBalance', 0),
                timestamp=datetime.now()
            )
            
            logger.info(f"Retrieved portfolio with {len(positions)} positions for account {account_id}")
            return portfolio
            
        except Exception as e:
            error_msg = f"Failed to get portfolio: {str(e)}"
            logger.error(error_msg)
            raise SchwabClientError(error_msg) from e
    
    def get_quote(self, symbols):
        """
        Get quotes for the specified symbols.
        
        Args:
            symbols (str or list): Symbol or list of symbols to get quotes for.
            
        Returns:
            dict: Quote data keyed by symbol.
            
        Raises:
            SchwabClientError: If the request fails.
        """
        try:
            # Convert single symbol to list
            if isinstance(symbols, str):
                symbols = [symbols]
                
            # Join symbols for the request
            symbols_str = ','.join(symbols)
            
            # Get quotes
            response = self.client.get_quotes(symbols=symbols_str)
            response.raise_for_status()
            quotes_data = response.json()
            
            logger.info(f"Retrieved quotes for {len(symbols)} symbols")
            return quotes_data
            
        except Exception as e:
            error_msg = f"Failed to get quotes: {str(e)}"
            logger.error(error_msg)
            raise SchwabClientError(error_msg) from e
    
    def get_price_history(self, symbol, period_type='day', period=10, 
                         frequency_type='minute', frequency=1):
        """
        Get price history for a symbol.
        
        Args:
            symbol (str): The symbol to get price history for.
            period_type (str): The type of period (day, month, year, ytd).
            period (int): The number of periods.
            frequency_type (str): The type of frequency (minute, daily, weekly, monthly).
            frequency (int): The frequency.
            
        Returns:
            pandas.DataFrame: Price history data.
            
        Raises:
            SchwabClientError: If the request fails.
        """
        try:
            # Get price history
            response = self.client.get_price_history(
                symbol=symbol,
                period_type=period_type,
                period=period,
                frequency_type=frequency_type,
                frequency=frequency
            )
            response.raise_for_status()
            history_data = response.json()
            
            # Convert to DataFrame
            candles = history_data.get('candles', [])
            if not candles:
                return pd.DataFrame()
                
            df = pd.DataFrame(candles)
            
            # Convert datetime
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            logger.info(f"Retrieved price history for {symbol} with {len(df)} data points")
            return df
            
        except Exception as e:
            error_msg = f"Failed to get price history: {str(e)}"
            logger.error(error_msg)
            raise SchwabClientError(error_msg) from e
    
    def place_order(self, order, account_id=None, dry_run=True):
        """
        Place an order.
        
        Args:
            order (dict): The order to place.
            account_id (str, optional): The account ID to place the order in.
                                        If None, uses the primary account.
            dry_run (bool): If True, validate but don't place the order.
            
        Returns:
            dict: Order response data.
            
        Raises:
            SchwabClientError: If the request fails.
        """
        try:
            # Use primary account if none specified
            if account_id is None:
                account_id = self.primary_account_id
                
            if not account_id:
                raise SchwabClientError("No account ID available")
            
            # Log the order
            log_msg = f"{'Validating' if dry_run else 'Placing'} order for {order.get('orderLegCollection', [{}])[0].get('instrument', {}).get('symbol')} in account {account_id}"
            logger.info(log_msg)
            
            if dry_run:
                # Validate the order without placing it
                # (schwab-py doesn't have a validate endpoint, so we'll just log it)
                logger.info(f"Dry run - would place order: {json.dumps(order)}")
                return {"dryRun": True, "order": order}
            else:
                # Place the order
                response = self.client.place_order(
                    account_id=account_id,
                    order_spec=order
                )
                response.raise_for_status()
                order_data = response.json()
                
                logger.info(f"Order placed successfully: {order_data.get('orderId')}")
                return order_data
                
        except Exception as e:
            error_msg = f"Failed to place order: {str(e)}"
            logger.error(error_msg)
            raise SchwabClientError(error_msg) from e
    
    def create_equity_order(self, symbol, quantity, instruction, price=None, dry_run=True):
        """
        Create and place an equity order.
        
        Args:
            symbol (str): The symbol to trade.
            quantity (float): The quantity to trade.
            instruction (str): 'BUY' or 'SELL'.
            price (float, optional): Limit price. If None, market order.
            dry_run (bool): If True, validate but don't place the order.
            
        Returns:
            dict: Order response data.
            
        Raises:
            SchwabClientError: If the request fails.
        """
        # Build the order
        order = {
            "orderType": "MARKET" if price is None else "LIMIT",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": instruction,
                    "quantity": quantity,
                    "instrument": {
                        "symbol": symbol,
                        "assetType": "EQUITY"
                    }
                }
            ]
        }
        
        # Add price for limit orders
        if price is not None:
            order["price"] = price
            
        # Place the order
        return self.place_order(order, dry_run=dry_run)