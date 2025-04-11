"""
Risk assessment module for the Schwab-AI Portfolio Manager.

This module provides risk assessment algorithms and metrics.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from src.schwab.portfolio import Portfolio, Position

logger = logging.getLogger(__name__)


def calculate_portfolio_risk(portfolio: Portfolio, historical_data: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, Any]:
    """
    Calculate comprehensive risk metrics for a portfolio.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        historical_data (Dict[str, pd.DataFrame], optional): Historical price data for positions.
        
    Returns:
        Dict[str, Any]: Risk assessment results.
    """
    logger.info("Calculating portfolio risk metrics")
    
    risk_metrics = {
        "overall_risk_score": 0,
        "diversification_risk": 0,
        "market_risk": 0,
        "volatility_risk": 0,
        "concentration_risk": 0,
        "sector_risk": 0,
        "position_risks": [],
    }
    
    # Calculate diversification risk (0-100, lower is better)
    diversification_risk = calculate_diversification_risk(portfolio)
    risk_metrics["diversification_risk"] = diversification_risk
    
    # Calculate concentration risk (0-100, lower is better)
    concentration_risk = calculate_concentration_risk(portfolio)
    risk_metrics["concentration_risk"] = concentration_risk
    
    # Calculate sector risk (0-100, lower is better)
    sector_risk = calculate_sector_risk(portfolio)
    risk_metrics["sector_risk"] = sector_risk
    
    # Calculate market risk if we have betas
    market_risk = calculate_market_risk(portfolio)
    risk_metrics["market_risk"] = market_risk
    
    # Calculate volatility risk if we have historical data
    if historical_data:
        volatility_risk = calculate_volatility_risk(portfolio, historical_data)
        risk_metrics["volatility_risk"] = volatility_risk
    
    # Calculate risk for individual positions
    position_risks = []
    for position in portfolio.positions:
        position_risk = calculate_position_risk(position, portfolio)
        position_risks.append({
            "symbol": position.symbol,
            "risk_score": position_risk,
            "weight": position.weight,
            "beta": position.instrument_data.get('fundamental', {}).get('beta', None),
        })
    
    risk_metrics["position_risks"] = position_risks
    
    # Calculate overall risk score (weighted average of all risk factors)
    overall_risk = 0.25 * diversification_risk + 0.25 * concentration_risk + \
                  0.2 * sector_risk + 0.3 * market_risk
    
    if "volatility_risk" in risk_metrics:
        # Recalculate with volatility included
        overall_risk = 0.2 * diversification_risk + 0.2 * concentration_risk + \
                      0.15 * sector_risk + 0.25 * market_risk + 0.2 * risk_metrics["volatility_risk"]
    
    risk_metrics["overall_risk_score"] = overall_risk
    
    return risk_metrics


def calculate_diversification_risk(portfolio: Portfolio) -> float:
    """
    Calculate diversification risk.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        
    Returns:
        float: Diversification risk score (0-100, lower is better).
    """
    if not portfolio.positions:
        return 0
    
    # Number of positions
    num_positions = len(portfolio.positions)
    
    # Base score based on number of positions
    if num_positions >= 20:
        base_score = 0
    elif num_positions >= 15:
        base_score = 20
    elif num_positions >= 10:
        base_score = 40
    elif num_positions >= 5:
        base_score = 60
    else:
        base_score = 80
    
    # Adjust score based on weight distribution
    weights = [p.weight for p in portfolio.positions]
    weight_std = np.std(weights) if weights else 0
    
    # Normalize standard deviation (higher std = less diversified)
    std_factor = min(weight_std * 2, 20)
    
    # Asset type diversification
    asset_types = set(p.asset_type for p in portfolio.positions)
    asset_type_factor = max(0, 20 - len(asset_types) * 5)
    
    # Combine factors
    diversification_risk = base_score + std_factor + asset_type_factor
    
    # Cap at 100
    return min(diversification_risk, 100)


def calculate_concentration_risk(portfolio: Portfolio) -> float:
    """
    Calculate concentration risk based on position weights.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        
    Returns:
        float: Concentration risk score (0-100, lower is better).
    """
    if not portfolio.positions:
        return 0
    
    # Calculate Herfindahl-Hirschman Index (HHI)
    weights = [p.weight / 100 for p in portfolio.positions]  # Convert to decimal
    hhi = sum(w**2 for w in weights)
    
    # Normalize HHI to 0-100 scale
    # HHI ranges from 1/n (perfect distribution) to 1 (complete concentration)
    n = len(portfolio.positions)
    min_hhi = 1 / n if n > 0 else 0
    normalized_hhi = (hhi - min_hhi) / (1 - min_hhi) if n > 1 else 1
    
    # Convert to risk score (0-100)
    concentration_risk = normalized_hhi * 100
    
    # Add penalty for positions over certain threshold
    for position in portfolio.positions:
        if position.weight > 10:
            # Add 2 points for each % over 10%
            concentration_risk += (position.weight - 10) * 2
    
    # Cap at 100
    return min(concentration_risk, 100)


def calculate_sector_risk(portfolio: Portfolio) -> float:
    """
    Calculate sector concentration risk.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        
    Returns:
        float: Sector risk score (0-100, lower is better).
    """
    if not portfolio.positions:
        return 0
    
    # Get sector allocations
    sector_allocations = portfolio.sector_allocations
    
    # Calculate sector HHI
    sector_weights = [allocation / 100 for allocation in sector_allocations.values()]
    sector_hhi = sum(w**2 for w in sector_weights)
    
    # Normalize HHI to 0-100 scale
    n = len(sector_allocations)
    min_hhi = 1 / n if n > 0 else 0
    normalized_hhi = (sector_hhi - min_hhi) / (1 - min_hhi) if n > 1 else 1
    
    # Convert to risk score (0-100)
    sector_risk = normalized_hhi * 100
    
    # Add penalty for sectors over certain threshold
    for sector, allocation in sector_allocations.items():
        if allocation > 25:
            # Add 3 points for each % over 25%
            sector_risk += (allocation - 25) * 3
    
    # Cap at 100
    return min(sector_risk, 100)


def calculate_market_risk(portfolio: Portfolio) -> float:
    """
    Calculate market risk based on portfolio beta.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        
    Returns:
        float: Market risk score (0-100, lower is not necessarily better).
    """
    # Calculate weighted average beta
    weighted_beta = 0
    total_weight_with_beta = 0
    
    for position in portfolio.positions:
        beta = position.instrument_data.get('fundamental', {}).get('beta')
        if beta is not None:
            weighted_beta += (position.weight / 100) * beta
            total_weight_with_beta += position.weight / 100
    
    # If we don't have beta for any positions, return middle value
    if total_weight_with_beta == 0:
        return 50
    
    # Normalize beta to account for positions without beta
    if total_weight_with_beta < 1:
        weighted_beta = weighted_beta / total_weight_with_beta
    
    # Convert beta to risk score
    # Beta of 1 = market risk = 50
    # Beta of 0 = no market risk = 0
    # Beta of 2 = high market risk = 100
    market_risk = 50 * weighted_beta
    
    # Cap between 0 and 100
    return max(0, min(market_risk, 100))


def calculate_volatility_risk(portfolio: Portfolio, historical_data: Dict[str, pd.DataFrame]) -> float:
    """
    Calculate volatility risk based on historical price data.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        historical_data (Dict[str, pd.DataFrame]): Historical price data for positions.
        
    Returns:
        float: Volatility risk score (0-100, lower is better).
    """
    # Calculate weighted average volatility
    weighted_volatility = 0
    total_weight_with_data = 0
    
    for position in portfolio.positions:
        if position.symbol in historical_data:
            df = historical_data[position.symbol]
            
            # Calculate daily returns
            if 'close' in df.columns:
                df['return'] = df['close'].pct_change()
                
                # Calculate annualized volatility (standard deviation * sqrt(252))
                volatility = df['return'].std() * (252 ** 0.5)
                
                weighted_volatility += (position.weight / 100) * volatility
                total_weight_with_data += position.weight / 100
    
    # If we don't have data for any positions, return middle value
    if total_weight_with_data == 0:
        return 50
    
    # Normalize volatility to account for positions without data
    if total_weight_with_data < 1:
        weighted_volatility = weighted_volatility / total_weight_with_data
    
    # Convert volatility to risk score
    # Benchmark: S&P 500 historical volatility is around 15-20%
    # 0% volatility = 0 risk
    # 20% volatility = 50 risk (market level)
    # 40% or higher volatility = 100 risk
    volatility_risk = (weighted_volatility / 0.4) * 100
    
    # Cap between 0 and 100
    return max(0, min(volatility_risk, 100))


def calculate_position_risk(position: Position, portfolio: Portfolio) -> float:
    """
    Calculate risk score for an individual position.
    
    Args:
        position (Position): The position to analyze.
        portfolio (Portfolio): The portfolio containing the position.
        
    Returns:
        float: Position risk score (0-100, lower is better).
    """
    risk_score = 0
    
    # Factor 1: Position size risk
    weight = position.weight
    if weight > 15:
        size_risk = 100
    elif weight > 10:
        size_risk = 50 + (weight - 10) * 10
    elif weight > 5:
        size_risk = (weight - 5) * 10
    else:
        size_risk = 0
    
    # Factor 2: Beta risk (if available)
    beta = position.instrument_data.get('fundamental', {}).get('beta')
    if beta is not None:
        beta_risk = max(0, min(beta * 50, 100))
    else:
        beta_risk = 50  # Default to medium risk if beta is unknown
    
    # Factor 3: Sector concentration risk
    sector = position.instrument_data.get('fundamental', {}).get('sector', 'Unknown')
    sector_allocation = portfolio.sector_allocations.get(sector, 0)
    
    if sector_allocation > 25:
        sector_risk = 50 + (sector_allocation - 25) * 2
    else:
        sector_risk = (sector_allocation / 25) * 50
    
    # Combine factors (weighted average)
    risk_score = 0.4 * size_risk + 0.4 * beta_risk + 0.2 * sector_risk
    
    return min(risk_score, 100)