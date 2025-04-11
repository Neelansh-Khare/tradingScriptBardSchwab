"""
Trade execution module for the Schwab-AI Portfolio Manager.

This module handles the execution of trade recommendations.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.schwab.client import SchwabClient
from src.analysis.recommendation import Recommendation

logger = logging.getLogger(__name__)


class TradeExecutionError(Exception):
    """Exception raised for trade execution errors."""
    pass


class ExecutedTrade:
    """
    Class representing an executed trade.
    """
    
    def __init__(self, symbol: str, action: str, quantity: float, price: Optional[float] = None, 
                order_id: Optional[str] = None, status: str = "pending"):
        """
        Initialize an executed trade.
        
        Args:
            symbol (str): The stock symbol.
            action (str): The action taken ('BUY' or 'SELL').
            quantity (float): The quantity traded.
            price (float, optional): The execution price.
            order_id (str, optional): The order ID from the broker.
            status (str): The trade status.
        """
        self.symbol = symbol
        self.action = action
        self.quantity = quantity
        self.price = price
        self.order_id = order_id
        self.status = status
        self.timestamp = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "order_id": self.order_id,
            "status": self.status,
            "timestamp": self.timestamp.isoformat()
        }


def execute_trades(recommendations: List[Recommendation], client: SchwabClient, 
                   config: Dict[str, Any]) -> List[ExecutedTrade]:
    """
    Execute trade recommendations.
    
    Args:
        recommendations (List[Recommendation]): Trade recommendations to execute.
        client (SchwabClient): Schwab client for executing trades.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        List[ExecutedTrade]: List of executed trades.
    """
    logger.info(f"Preparing to execute {len(recommendations)} trade recommendations")
    
    # Check if dry run mode is enabled
    dry_run = config.get("DRY_RUN", True)
    if dry_run:
        logger.info("DRY RUN MODE: No actual trades will be executed")
    
    # Check if auto trading is enabled
    auto_trading_enabled = config.get("ENABLE_AUTO_TRADING", False)
    if not auto_trading_enabled:
        logger.info("Auto trading is disabled in config. No trades will be executed")
        return []
    
    # Get account ID to use
    account_id = config.get("SCHWAB_ACCOUNT_ID", None)
    
    # Sort recommendations by priority
    sorted_recommendations = sorted(recommendations, key=lambda x: x.priority, reverse=True)
    
    # Maximum number of trades per session
    max_trades = config.get("MAX_TRADES_PER_SESSION", 5)
    
    # Execute trades
    executed_trades = []
    for i, recommendation in enumerate(sorted_recommendations):
        if i >= max_trades:
            logger.info(f"Reached maximum trades per session ({max_trades}). Stopping execution")
            break
            
        try:
            logger.info(f"Executing trade recommendation: {recommendation}")
            
            # Validate the trade
            from src.trading.validation import validate_trade
            validation_result = validate_trade(recommendation, client, config)
            
            if not validation_result["valid"]:
                logger.warning(f"Trade validation failed: {validation_result['reason']}")
                continue
            
            # Get the validated quantity
            quantity = validation_result["quantity"]
            
            # Execute the trade
            executed_trade = execute_single_trade(recommendation, quantity, client, account_id, dry_run)
            executed_trades.append(executed_trade)
            
            logger.info(f"Trade executed: {executed_trade.action} {executed_trade.quantity} shares of {executed_trade.symbol}")
            
            # Wait between trades to avoid rate limiting
            if i < len(sorted_recommendations) - 1:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
    
    logger.info(f"Executed {len(executed_trades)} out of {len(recommendations)} recommendations")
    return executed_trades


def execute_single_trade(recommendation: Recommendation, quantity: float, 
                        client: SchwabClient, account_id: Optional[str] = None,
                        dry_run: bool = True) -> ExecutedTrade:
    """
    Execute a single trade.
    
    Args:
        recommendation (Recommendation): The trade recommendation.
        quantity (float): The quantity to trade.
        client (SchwabClient): Schwab client for executing trades.
        account_id (str, optional): The account ID to trade in.
        dry_run (bool): If True, simulate but don't execute the trade.
        
    Returns:
        ExecutedTrade: The executed trade object.
        
    Raises:
        TradeExecutionError: If the trade fails.
    """
    try:
        symbol = recommendation.symbol
        action = recommendation.action
        
        # Convert action to Schwab format
        instruction = "BUY" if action == "BUY" else "SELL"
        
        # Create a market order
        order_result = client.create_equity_order(
            symbol=symbol,
            quantity=quantity,
            instruction=instruction,
            price=None,  # Market order
            dry_run=dry_run
        )
        
        # Create executed trade object
        if dry_run:
            # For dry run, we don't have an order ID or price
            executed_trade = ExecutedTrade(
                symbol=symbol,
                action=action,
                quantity=quantity,
                status="simulated"
            )
        else:
            # Extract order ID and status from result
            order_id = order_result.get("orderId", None)
            status = "completed" if order_id else "failed"
            
            executed_trade = ExecutedTrade(
                symbol=symbol,
                action=action,
                quantity=quantity,
                order_id=order_id,
                status=status
            )
        
        return executed_trade
        
    except Exception as e:
        error_msg = f"Failed to execute trade for {recommendation.symbol}: {str(e)}"
        logger.error(error_msg)
        raise TradeExecutionError(error_msg) from e