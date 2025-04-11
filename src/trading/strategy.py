"""
Trading strategies for the Schwab-AI Portfolio Manager.

This module implements various risk-averse trading strategies.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from src.schwab.portfolio import Portfolio, Position
from src.analysis.recommendation import Recommendation

logger = logging.getLogger(__name__)


class TradingStrategy:
    """
    Base class for trading strategies.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the trading strategy.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        
    def generate_recommendations(self, portfolio: Portfolio, 
                               analysis_results: Dict[str, Any]) -> List[Recommendation]:
        """
        Generate trade recommendations based on portfolio analysis.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            analysis_results (Dict[str, Any]): Analysis results.
            
        Returns:
            List[Recommendation]: List of trade recommendations.
        """
        raise NotImplementedError("Subclasses must implement this method")


class RiskAverseStrategy(TradingStrategy):
    """
    Risk-averse trading strategy focused on capital preservation.
    """
    
    def generate_recommendations(self, portfolio: Portfolio, 
                               analysis_results: Dict[str, Any]) -> List[Recommendation]:
        """
        Generate trade recommendations with a risk-averse approach.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            analysis_results (Dict[str, Any]): Analysis results.
            
        Returns:
            List[Recommendation]: List of trade recommendations.
        """
        recommendations = []
        
        # Extract risk metrics
        risk_metrics = analysis_results.get("risk_metrics", {})
        
        # Extract risk profile from config
        risk_tolerance = int(self.config.get("RISK_TOLERANCE", 5))
        max_position_size = float(self.config.get("MAX_POSITION_SIZE_PERCENT", 10))
        max_sector_exposure = float(self.config.get("MAX_SECTOR_EXPOSURE_PERCENT", 25))
        
        # Check for excessive position sizes
        self._check_position_sizes(portfolio, max_position_size, recommendations)
        
        # Check for excessive sector exposures
        self._check_sector_exposures(portfolio, max_sector_exposure, recommendations)
        
        # Check for high-risk positions
        self._check_high_risk_positions(portfolio, risk_metrics, risk_tolerance, recommendations)
        
        # Check for cash deployment opportunities
        self._check_cash_deployment(portfolio, recommendations)
        
        # Check for rebalancing opportunities
        self._check_rebalancing_opportunities(portfolio, recommendations)
        
        # Sort recommendations by priority
        recommendations.sort(key=lambda x: x.priority, reverse=True)
        
        return recommendations
    
    def _check_position_sizes(self, portfolio: Portfolio, max_position_size: float,
                             recommendations: List[Recommendation]) -> None:
        """
        Check for positions that exceed maximum size and recommend trimming.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            max_position_size (float): Maximum position size percentage.
            recommendations (List[Recommendation]): List to add recommendations to.
        """
        for position in portfolio.positions:
            if position.weight > max_position_size:
                excess_pct = position.weight - max_position_size
                reduction_pct = (excess_pct / position.weight) * 100
                
                # Round to nearest percentage point
                reduction_pct = round(reduction_pct)
                
                recommendation = Recommendation(
                    action="SELL",
                    symbol=position.symbol,
                    percentage=reduction_pct,
                    rationale=f"Position exceeds maximum size of {max_position_size}%. Reducing to compliance level."
                )
                recommendation.priority = 10  # High priority
                recommendations.append(recommendation)
    
    def _check_sector_exposures(self, portfolio: Portfolio, max_sector_exposure: float,
                               recommendations: List[Recommendation]) -> None:
        """
        Check for sectors that exceed maximum exposure and recommend rebalancing.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            max_sector_exposure (float): Maximum sector exposure percentage.
            recommendations (List[Recommendation]): List to add recommendations to.
        """
        for sector, allocation in portfolio.sector_allocations.items():
            if allocation > max_sector_exposure:
                excess_pct = allocation - max_sector_exposure
                
                # Find positions in this sector
                sector_positions = []
                for position in portfolio.positions:
                    position_sector = position.instrument_data.get('fundamental', {}).get('sector', 'Unknown')
                    if position_sector == sector:
                        sector_positions.append(position)
                
                if not sector_positions:
                    continue
                
                # Sort by weight (largest first)
                sector_positions.sort(key=lambda p: p.weight, reverse=True)
                
                # Recommend selling from largest position
                largest_position = sector_positions[0]
                
                # Calculate what percentage to reduce by
                reduction_value = (excess_pct / 100) * portfolio.account_value
                position_reduction_pct = min((reduction_value / largest_position.market_value) * 100, 50)
                
                # Round to nearest percentage point
                position_reduction_pct = round(position_reduction_pct)
                
                if position_reduction_pct > 0:
                    recommendation = Recommendation(
                        action="SELL",
                        symbol=largest_position.symbol,
                        percentage=position_reduction_pct,
                        rationale=f"Sector {sector} exceeds maximum exposure of {max_sector_exposure}%. Reducing largest position."
                    )
                    recommendation.priority = 9  # High priority
                    recommendations.append(recommendation)
    
    def _check_high_risk_positions(self, portfolio: Portfolio, risk_metrics: Dict[str, Any],
                                  risk_tolerance: int, recommendations: List[Recommendation]) -> None:
        """
        Check for high-risk positions and recommend reducing or replacing.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            risk_metrics (Dict[str, Any]): Risk metrics.
            risk_tolerance (int): Risk tolerance (1-10, 1 is most conservative).
            recommendations (List[Recommendation]): List to add recommendations to.
        """
        # Get position risk scores
        position_risks = risk_metrics.get("position_risks", [])
        
        # Define risk threshold based on risk tolerance
        risk_threshold = 100 - (risk_tolerance * 10)
        
        for position_risk in position_risks:
            symbol = position_risk.get("symbol")
            risk_score = position_risk.get("risk_score", 0)
            
            if risk_score > risk_threshold:
                position = portfolio.get_position_by_symbol(symbol)
                if position is None:
                    continue
                
                # Calculate what percentage to reduce by
                excess_risk = risk_score - risk_threshold
                reduction_pct = min(excess_risk, 50)  # Cap at 50%
                
                # Round to nearest percentage point
                reduction_pct = round(reduction_pct)
                
                if reduction_pct > 0:
                    recommendation = Recommendation(
                        action="SELL",
                        symbol=symbol,
                        percentage=reduction_pct,
                        rationale=f"Position has high risk score ({risk_score:.1f}/100). Reducing exposure."
                    )
                    recommendation.priority = 8  # Medium-high priority
                    recommendations.append(recommendation)
    
    def _check_cash_deployment(self, portfolio: Portfolio, 
                              recommendations: List[Recommendation]) -> None:
        """
        Check for cash deployment opportunities.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            recommendations (List[Recommendation]): List to add recommendations to.
        """
        # Define target cash percentage based on risk tolerance
        risk_tolerance = int(self.config.get("RISK_TOLERANCE", 5))
        target_cash_pct = max(5, 20 - risk_tolerance * 1.5)
        
        current_cash_pct = portfolio.cash_allocation
        
        # If cash is significantly above target, recommend deployment
        if current_cash_pct > target_cash_pct + 10:
            excess_cash_pct = current_cash_pct - target_cash_pct
            
            # Define deployment strategy based on portfolio size
            if len(portfolio.positions) < 15:
                # Recommend adding a new position
                recommendation = Recommendation(
                    action="BUY",
                    symbol="VTI",  # Default to a safe ETF
                    percentage=excess_cash_pct / 2,  # Deploy half of excess cash
                    rationale=f"Cash allocation ({current_cash_pct:.1f}%) above target ({target_cash_pct:.1f}%). Recommending broad-market ETF for diversification."
                )
                recommendation.priority = 5  # Medium priority
                recommendations.append(recommendation)
            else:
                # Recommend increasing existing safe positions
                for position in portfolio.positions:
                    # Check if position is an ETF or blue-chip stock
                    is_safe = position.asset_type == "ETF" or (
                        position.instrument_data.get('fundamental', {}).get('beta', 1.5) < 1.0
                    )
                    
                    # Check if position is already near max size
                    max_position_size = float(self.config.get("MAX_POSITION_SIZE_PERCENT", 10))
                    is_small = position.weight < max_position_size / 2
                    
                    if is_safe and is_small:
                        recommendation = Recommendation(
                            action="BUY",
                            symbol=position.symbol,
                            percentage=excess_cash_pct / 3,  # Deploy a third of excess cash
                            rationale=f"Cash allocation ({current_cash_pct:.1f}%) above target ({target_cash_pct:.1f}%). Increasing position in low-risk asset."
                        )
                        recommendation.priority = 5  # Medium priority
                        recommendations.append(recommendation)
                        break
    
    def _check_rebalancing_opportunities(self, portfolio: Portfolio,
                                        recommendations: List[Recommendation]) -> None:
        """
        Check for rebalancing opportunities to improve diversification.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            recommendations (List[Recommendation]): List to add recommendations to.
        """
        # Skip if fewer than 3 positions
        if len(portfolio.positions) < 3:
            return
        
        # Calculate standard deviation of position weights
        weights = [p.weight for p in portfolio.positions]
        weight_std = np.std(weights)
        
        # If weights are very uneven, recommend rebalancing
        if weight_std > 8:  # Arbitrary threshold
            # Sort positions by weight (largest first)
            sorted_positions = sorted(portfolio.positions, key=lambda p: p.weight, reverse=True)
            
            # Get largest and smallest positions
            largest_position = sorted_positions[0]
            smallest_position = sorted_positions[-1]
            
            # Only recommend if there's a significant difference
            if largest_position.weight > 3 * smallest_position.weight and smallest_position.weight > 0:
                # Calculate amount to transfer (about 20% of the difference)
                weight_diff = largest_position.weight - smallest_position.weight
                transfer_pct = round(weight_diff * 0.2)
                
                if transfer_pct >= 5:  # Only if meaningful (at least 5%)
                    # Recommend selling from largest position
                    sell_rec = Recommendation(
                        action="SELL",
                        symbol=largest_position.symbol,
                        percentage=transfer_pct,
                        rationale=f"Portfolio weights are uneven (std dev: {weight_std:.1f}%). Rebalancing from largest to smallest position."
                    )
                    sell_rec.priority = 6  # Medium priority
                    recommendations.append(sell_rec)
                    
                    # Recommend buying smallest position
                    buy_rec = Recommendation(
                        action="BUY",
                        symbol=smallest_position.symbol,
                        percentage=transfer_pct,
                        rationale=f"Portfolio weights are uneven (std dev: {weight_std:.1f}%). Rebalancing from largest to smallest position."
                    )
                    buy_rec.priority = 6  # Medium priority
                    recommendations.append(buy_rec)


class DefinedRiskStrategy(TradingStrategy):
    """
    Trading strategy with defined risk parameters with a focus on risk-adjusted returns.
    """
    
    def generate_recommendations(self, portfolio: Portfolio, 
                               analysis_results: Dict[str, Any]) -> List[Recommendation]:
        """
        Generate trade recommendations with defined risk parameters.
        
        Args:
            portfolio (Portfolio): The portfolio to analyze.
            analysis_results (Dict[str, Any]): Analysis results.
            
        Returns:
            List[Recommendation]: List of trade recommendations.
        """
        # Implementation would go here, following similar pattern as RiskAverseStrategy
        # This would include position sizing, hedging, and more sophisticated risk management
        
        # For now, we'll return an empty list
        return []