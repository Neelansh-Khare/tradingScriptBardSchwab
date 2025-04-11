"""
Trade validation module for the Schwab-AI Portfolio Manager.

This module validates trade recommendations before execution.
"""

import logging
from typing import Dict, Any, List, Optional

from src.schwab.client import SchwabClient
from src.analysis.recommendation import Recommendation

logger = logging.getLogger(__name__)


def validate_trade(recommendation: Recommendation, client: SchwabClient, 
                  config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a trade recommendation.
    
    Args:
        recommendation (Recommendation): The trade recommendation.
        client (SchwabClient): Schwab client for market data.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        Dict[str, Any]: Validation result including:
            - valid (bool): Whether the trade is valid
            - reason (str): Reason for invalidity if not valid
            - quantity (float): Validated quantity
    """
    logger.info(f"Validating trade: {recommendation.action} {recommendation.symbol}")
    
    # Initialize result
    result = {
        "valid": False,
        "reason": "",
        "quantity": 0.0
    }
    
    # Validate symbol
    if not validate_symbol(recommendation.symbol, client):
        result["reason"] = f"Invalid symbol: {recommendation.symbol}"
        return result
    
    # Get position and quote data
    try:
        portfolio = client.get_portfolio()
        position = portfolio.get_position_by_symbol(recommendation.symbol)
        
        quotes = client.get_quote([recommendation.symbol])
        quote = quotes.get(recommendation.symbol, {})
        
        current_price = quote.get("lastPrice", 0)
        if current_price == 0:
            result["reason"] = f"Could not get current price for {recommendation.symbol}"
            return result
            
    except Exception as e:
        result["reason"] = f"Failed to get position or quote data: {str(e)}"
        return result
    
    # Validate quantity
    quantity_result = validate_quantity(
        recommendation=recommendation,
        position=position,
        portfolio=portfolio,
        current_price=current_price,
        config=config
    )
    
    if not quantity_result["valid"]:
        result["reason"] = quantity_result["reason"]
        return result
    
    # Set quantity
    result["quantity"] = quantity_result["quantity"]
    
    # Validate based on action
    if recommendation.action == "BUY":
        buy_validation = validate_buy(
            recommendation=recommendation,
            portfolio=portfolio,
            quantity=result["quantity"],
            current_price=current_price,
            config=config
        )
        
        if not buy_validation["valid"]:
            result["reason"] = buy_validation["reason"]
            return result
            
    elif recommendation.action == "SELL":
        sell_validation = validate_sell(
            recommendation=recommendation,
            position=position,
            quantity=result["quantity"],
            config=config
        )
        
        if not sell_validation["valid"]:
            result["reason"] = sell_validation["reason"]
            return result
    
    # All validations passed
    result["valid"] = True
    return result


def validate_symbol(symbol: str, client: SchwabClient) -> bool:
    """
    Validate that a symbol exists and is tradable.
    
    Args:
        symbol (str): The stock symbol.
        client (SchwabClient): Schwab client for market data.
        
    Returns:
        bool: Whether the symbol is valid.
    """
    try:
        # Get quote for the symbol
        quotes = client.get_quote([symbol])
        return symbol in quotes
    except Exception as e:
        logger.error(f"Error validating symbol {symbol}: {str(e)}")
        return False


def validate_quantity(recommendation: Recommendation, position, portfolio, 
                     current_price: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and determine the quantity to trade.
    
    Args:
        recommendation (Recommendation): The trade recommendation.
        position: The current position (None if not owned).
        portfolio: The portfolio.
        current_price (float): Current market price.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        Dict[str, Any]: Validation result including:
            - valid (bool): Whether the quantity is valid
            - reason (str): Reason for invalidity if not valid
            - quantity (float): Validated quantity
    """
    result = {
        "valid": False,
        "reason": "",
        "quantity": 0.0
    }
    
    # Case 1: Recommendation specifies quantity directly
    if recommendation.quantity is not None:
        quantity = recommendation.quantity
        
        # For sell orders, validate against current position
        if recommendation.action == "SELL":
            if position is None or position.quantity < quantity:
                max_quantity = 0 if position is None else position.quantity
                result["reason"] = f"Recommended sell quantity ({quantity}) exceeds current position ({max_quantity})"
                return result
    
    # Case 2: Recommendation specifies percentage
    elif recommendation.percentage is not None:
        percentage = recommendation.percentage
        
        if recommendation.action == "BUY":
            # Calculate quantity based on percentage of cash
            cash = portfolio.cash_balance
            value_to_trade = cash * (percentage / 100)
            quantity = value_to_trade / current_price if current_price > 0 else 0
            
            # Round down to nearest whole share
            quantity = int(quantity)
            
            if quantity <= 0:
                result["reason"] = f"Insufficient cash to buy {percentage}% of cash balance"
                return result
                
        elif recommendation.action == "SELL":
            # Calculate quantity based on percentage of position
            if position is None:
                result["reason"] = f"Cannot sell {percentage}% of non-existent position"
                return result
                
            quantity = position.quantity * (percentage / 100)
            
            # Round down to nearest whole share
            quantity = int(quantity)
            
            if quantity <= 0:
                result["reason"] = f"Sell percentage results in zero shares"
                return result
    
    # Case 3: No quantity or percentage specified
    else:
        # Default to 100% for sells or a reasonable value for buys
        if recommendation.action == "SELL":
            if position is None:
                result["reason"] = "Cannot sell non-existent position"
                return result
                
            quantity = position.quantity
            
        else:  # BUY
            # Default to 5% of cash balance
            cash = portfolio.cash_balance
            default_percentage = 5
            value_to_trade = cash * (default_percentage / 100)
            quantity = value_to_trade / current_price if current_price > 0 else 0
            
            # Round down to nearest whole share
            quantity = int(quantity)
            
            if quantity <= 0:
                result["reason"] = "Insufficient cash for default buy quantity"
                return result
    
    # Apply minimum and maximum quantity limits
    min_quantity = config.get("MIN_TRADE_QUANTITY", 1)
    max_quantity = config.get("MAX_TRADE_QUANTITY", 10000)
    
    if quantity < min_quantity:
        result["reason"] = f"Quantity ({quantity}) below minimum ({min_quantity})"
        return result
        
    if quantity > max_quantity:
        quantity = max_quantity
    
    # Set the quantity
    result["quantity"] = quantity
    result["valid"] = True
    
    return result


def validate_buy(recommendation: Recommendation, portfolio, quantity: float,
                current_price: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a buy order.
    
    Args:
        recommendation (Recommendation): The trade recommendation.
        portfolio: The portfolio.
        quantity (float): The quantity to buy.
        current_price (float): Current market price.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        Dict[str, Any]: Validation result including:
            - valid (bool): Whether the order is valid
            - reason (str): Reason for invalidity if not valid
    """
    result = {
        "valid": False,
        "reason": ""
    }
    
    # Check if we have enough cash
    cash_balance = portfolio.cash_balance
    cost = quantity * current_price
    
    if cost > cash_balance:
        result["reason"] = f"Insufficient cash (${cash_balance:.2f}) for trade (${cost:.2f})"
        return result
        
    # Check minimum cash reserve
    min_cash_reserve = config.get("MIN_CASH_RESERVE_PERCENT", 5)
    min_cash_amount = portfolio.account_value * (min_cash_reserve / 100)
    
    remaining_cash = cash_balance - cost
    if remaining_cash < min_cash_amount:
        result["reason"] = f"Trade would reduce cash below minimum reserve (${min_cash_amount:.2f})"
        return result
    
    # Check position size limits
    max_position_size = config.get("MAX_POSITION_SIZE_PERCENT", 10)
    
    # Calculate new position size
    existing_position = portfolio.get_position_by_symbol(recommendation.symbol)
    existing_value = 0 if existing_position is None else existing_position.market_value
    new_value = existing_value + cost
    new_weight = (new_value / (portfolio.account_value + cost - existing_value)) * 100
    
    if new_weight > max_position_size:
        result["reason"] = f"Trade would create position exceeding maximum size ({max_position_size}%)"
        return result
    
    # All validations passed
    result["valid"] = True
    return result


def validate_sell(recommendation: Recommendation, position, quantity: float,
                config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a sell order.
    
    Args:
        recommendation (Recommendation): The trade recommendation.
        position: The current position.
        quantity (float): The quantity to sell.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        Dict[str, Any]: Validation result including:
            - valid (bool): Whether the order is valid
            - reason (str): Reason for invalidity if not valid
    """
    result = {
        "valid": False,
        "reason": ""
    }
    
    # Check if position exists
    if position is None:
        result["reason"] = f"Cannot sell non-existent position: {recommendation.symbol}"
        return result
    
    # Check if we have enough shares
    if quantity > position.quantity:
        result["reason"] = f"Insufficient shares ({position.quantity}) for sale ({quantity})"
        return result
    
    # Check minimum position size
    min_position_size = config.get("MIN_POSITION_SIZE", 1)
    
    new_quantity = position.quantity - quantity
    if 0 < new_quantity < min_position_size:
        result["reason"] = f"Sale would reduce position below minimum size ({min_position_size} shares)"
        return result
    
    # All validations passed
    result["valid"] = True
    return result