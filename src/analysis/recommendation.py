"""
Portfolio analysis module for the Schwab-AI Portfolio Manager.

This module analyzes portfolio data to generate insights and recommendations.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List

import pandas as pd
import numpy as np

from src.schwab.portfolio import Portfolio
from src.llm.client import BaseLLMClient
from src.llm.prompts import PromptTemplates

logger = logging.getLogger(__name__)


def analyze_portfolio(portfolio: Portfolio, llm_client: BaseLLMClient, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a portfolio using various methods including LLM insights.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        llm_client (BaseLLMClient): LLM client for generating insights.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        Dict[str, Any]: Analysis results.
    """
    logger.info(f"Analyzing portfolio for account {portfolio.account_id}")
    
    # Initialize results dictionary
    results = {
        "timestamp": datetime.now().isoformat(),
        "account_id": portfolio.account_id,
        "metrics": {},
        "insights": {},
        "risk_metrics": {},
        "llm_analysis": {},
    }
    
    # Calculate basic portfolio metrics
    metrics = calculate_portfolio_metrics(portfolio)
    results["metrics"] = metrics
    logger.info("Calculated basic portfolio metrics")
    
    # Calculate risk metrics
    risk_metrics = calculate_risk_metrics(portfolio)
    results["risk_metrics"] = risk_metrics
    logger.info("Calculated portfolio risk metrics")
    
    # Get market data for context
    market_data = get_market_data()
    logger.info("Retrieved market data for context")
    
    # Get LLM analysis
    llm_analysis = get_llm_analysis(portfolio, market_data, config, llm_client)
    results["llm_analysis"] = llm_analysis
    logger.info("Generated LLM analysis for portfolio")
    
    # Generate insights
    insights = generate_insights(portfolio, metrics, risk_metrics, llm_analysis)
    results["insights"] = insights
    logger.info("Generated portfolio insights")
    
    return results


def calculate_portfolio_metrics(portfolio: Portfolio) -> Dict[str, Any]:
    """
    Calculate basic portfolio metrics.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        
    Returns:
        Dict[str, Any]: Portfolio metrics.
    """
    # Create DataFrame for calculations
    df = portfolio.to_dataframe()
    
    # Skip if no positions
    if len(df) == 0:
        return {
            "diversity_score": 0,
            "concentration_score": 0,
            "average_weight": 0,
            "top_holdings": [],
            "sector_concentration": 0,
        }
    
    # Diversity score (higher is better)
    weights = df['weight'].values
    diversity_score = 1 - np.std(weights) / max(np.mean(weights), 0.01)
    
    # Concentration score (lower is better)
    concentration_score = sum(w**2 for w in weights) / sum(weights)**2
    
    # Top holdings
    top_holdings = df.sort_values('weight', ascending=False).head(5)[['symbol', 'weight']].to_dict('records')
    
    # Sector concentration
    sector_data = {}
    for position in portfolio.positions:
        sector = position.instrument_data.get('fundamental', {}).get('sector', 'Unknown')
        if sector not in sector_data:
            sector_data[sector] = 0
        sector_data[sector] += position.weight
    
    # Calculate Herfindahl-Hirschman Index for sectors
    sector_values = list(sector_data.values())
    sector_concentration = sum(s**2 for s in sector_values) / 10000  # Scale to 0-1
    
    return {
        "diversity_score": float(diversity_score),
        "concentration_score": float(concentration_score),
        "average_weight": float(df['weight'].mean()),
        "top_holdings": top_holdings,
        "sector_concentration": float(sector_concentration),
        "sector_data": sector_data,
    }


def calculate_risk_metrics(portfolio: Portfolio) -> Dict[str, Any]:
    """
    Calculate risk metrics for the portfolio.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        
    Returns:
        Dict[str, Any]: Risk metrics.
    """
    # Create DataFrame for calculations
    df = portfolio.to_dataframe()
    
    # Skip if no positions
    if len(df) == 0:
        return {
            "beta": 0,
            "volatility": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0,
            "risk_concentration": 0,
        }
    
    # Extract betas from instrument data (if available)
    betas = []
    for position in portfolio.positions:
        beta = position.instrument_data.get('fundamental', {}).get('beta', None)
        if beta is not None:
            betas.append((position.weight / 100) * beta)
    
    # Portfolio beta (weighted average)
    portfolio_beta = sum(betas) if betas else None
    
    # We would need historical data for volatility, max drawdown, and Sharpe ratio
    # For now, we'll use placeholders or simplified calculations
    
    # Risk concentration (percentage of portfolio in high-beta stocks)
    high_beta_weight = 0
    for position in portfolio.positions:
        beta = position.instrument_data.get('fundamental', {}).get('beta', None)
        if beta is not None and beta > 1.2:  # Arbitrary threshold
            high_beta_weight += position.weight
    
    return {
        "beta": portfolio_beta,
        "volatility": None,  # Requires historical data
        "max_drawdown": None,  # Requires historical data
        "sharpe_ratio": None,  # Requires historical data
        "risk_concentration": float(high_beta_weight),
    }


def get_market_data() -> Dict[str, Any]:
    """
    Get market data for context.
    
    Returns:
        Dict[str, Any]: Market data.
    """
    # This would normally fetch data from an API or data provider
    # For now, we'll use placeholder data
    
    return {
        "indices": {
            "S&P 500": {"current": 5021.84, "change_percent": 0.32},
            "Dow Jones": {"current": 38671.69, "change_percent": 0.05},
            "Nasdaq": {"current": 16795.55, "change_percent": 0.35},
        },
        "sector_performance": {
            "Technology": {"performance": 0.48},
            "Healthcare": {"performance": -0.12},
            "Financials": {"performance": 0.23},
            "Consumer Discretionary": {"performance": 0.15},
            "Industrials": {"performance": 0.18},
            "Energy": {"performance": -0.35},
            "Materials": {"performance": 0.08},
            "Utilities": {"performance": -0.22},
            "Real Estate": {"performance": -0.10},
            "Consumer Staples": {"performance": 0.05},
            "Communication Services": {"performance": 0.30},
        },
        "economic_indicators": {
            "10Y Treasury": 3.87,
            "VIX": 14.32,
            "Inflation Rate": 3.2,
            "Unemployment Rate": 3.8,
        }
    }


def get_llm_analysis(portfolio: Portfolio, market_data: Dict[str, Any], 
                     config: Dict[str, Any], llm_client: BaseLLMClient) -> Dict[str, Any]:
    """
    Get LLM-based analysis of the portfolio.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        market_data (Dict[str, Any]): Market data for context.
        config (Dict[str, Any]): Configuration dictionary.
        llm_client (BaseLLMClient): LLM client for generating analysis.
        
    Returns:
        Dict[str, Any]: LLM analysis results.
    """
    # Extract risk profile from config
    risk_profile = {
        "risk_tolerance": int(config.get("RISK_TOLERANCE", 5)),
        "max_position_size_percent": float(config.get("MAX_POSITION_SIZE_PERCENT", 10)),
        "max_sector_exposure_percent": float(config.get("MAX_SECTOR_EXPOSURE_PERCENT", 25)),
    }
    
    # Prepare data for the prompt
    portfolio_data = portfolio.to_dict()
    
    # Generate prompt
    prompt = PromptTemplates.portfolio_analysis(
        portfolio_data=portfolio_data,
        market_data=market_data,
        risk_profile=risk_profile
    )
    
    # Get analysis from LLM
    logger.info("Requesting portfolio analysis from LLM")
    analysis_text = llm_client.generate(
        prompt=prompt,
        temperature=0.2,
        max_tokens=3000
    )
    
    # Parse the analysis text
    analysis_results = parse_llm_analysis(analysis_text)
    
    # Return both raw text and parsed results
    return {
        "raw_text": analysis_text,
        "parsed_results": analysis_results
    }


def parse_llm_analysis(analysis_text: str) -> Dict[str, Any]:
    """
    Parse the LLM analysis text into structured data.
    
    This is a simple implementation that extracts key sections.
    A more robust implementation would use regex or better parsing.
    
    Args:
        analysis_text (str): The raw LLM analysis text.
        
    Returns:
        Dict[str, Any]: Structured analysis data.
    """
    # Simple parsing based on common section headers
    sections = {
        "portfolio_assessment": "",
        "strengths": [],
        "vulnerabilities": [],
        "positions_needing_attention": [],
        "rebalancing_recommendations": [],
        "cash_deployment_suggestions": []
    }
    
    # Split into lines for processing
    lines = analysis_text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for section headers
        lower_line = line.lower()
        
        if "assessment" in lower_line and "portfolio" in lower_line:
            current_section = "portfolio_assessment"
            sections[current_section] = ""
        elif "strength" in lower_line:
            current_section = "strengths"
            sections[current_section] = []
        elif "vulnerabilit" in lower_line or "weakness" in lower_line:
            current_section = "vulnerabilities"
            sections[current_section] = []
        elif "attention" in lower_line and "position" in lower_line:
            current_section = "positions_needing_attention"
            sections[current_section] = []
        elif "rebalancing" in lower_line:
            current_section = "rebalancing_recommendations"
            sections[current_section] = []
        elif "cash" in lower_line and "deploy" in lower_line:
            current_section = "cash_deployment_suggestions"
            sections[current_section] = []
        elif current_section:
            # Process content based on section type
            if current_section == "portfolio_assessment":
                sections[current_section] += line + " "
            elif current_section in ["strengths", "vulnerabilities", "positions_needing_attention",
                                    "rebalancing_recommendations", "cash_deployment_suggestions"]:
                # Check for bullet points
                if line.startswith("-") or line.startswith("*"):
                    sections[current_section].append(line[1:].strip())
                elif sections[current_section] and not line.startswith(("#", "##", "###")):
                    # Append to the last item if not a header
                    if sections[current_section]:
                        sections[current_section][-1] += " " + line
    
    # Extract positions needing attention in a more structured format
    structured_positions = []
    for position in sections["positions_needing_attention"]:
        symbol = None
        reason = position
        
        # Try to extract symbol (assuming format like "AAPL: reason")
        if ":" in position:
            parts = position.split(":", 1)
            symbol_part = parts[0].strip().upper()
            reason = parts[1].strip()
            
            # Extract just the symbol (likely uppercase letters)
            import re
            match = re.search(r'\b[A-Z]+\b', symbol_part)
            if match:
                symbol = match.group(0)
        
        if symbol:
            structured_positions.append({"symbol": symbol, "reason": reason})
    
    if structured_positions:
        sections["positions_needing_attention"] = structured_positions
        
    return sections


def generate_insights(portfolio: Portfolio, metrics: Dict[str, Any], 
                     risk_metrics: Dict[str, Any], llm_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate insights from portfolio analysis.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        metrics (Dict[str, Any]): Basic portfolio metrics.
        risk_metrics (Dict[str, Any]): Risk metrics.
        llm_analysis (Dict[str, Any]): LLM analysis results.
        
    Returns:
        Dict[str, Any]: Portfolio insights.
    """
    insights = {}
    
    # Diversity insights
    diversity_score = metrics.get("diversity_score", 0)
    if diversity_score < 0.5:
        insights["diversity"] = {
            "status": "concerning",
            "message": "Portfolio diversity is low, consider reducing concentration in top holdings."
        }
    elif diversity_score < 0.7:
        insights["diversity"] = {
            "status": "fair",
            "message": "Portfolio diversity is acceptable but could be improved."
        }
    else:
        insights["diversity"] = {
            "status": "good",
            "message": "Portfolio has good diversification across holdings."
        }
    
    # Risk insights
    portfolio_beta = risk_metrics.get("beta")
    if portfolio_beta is not None:
        if portfolio_beta > 1.2:
            insights["risk"] = {
                "status": "high",
                "message": f"Portfolio beta ({portfolio_beta:.2f}) is high, suggesting above-market risk."
            }
        elif portfolio_beta < 0.8:
            insights["risk"] = {
                "status": "low",
                "message": f"Portfolio beta ({portfolio_beta:.2f}) is low, suggesting below-market risk."
            }
        else:
            insights["risk"] = {
                "status": "moderate",
                "message": f"Portfolio beta ({portfolio_beta:.2f}) is near market level."
            }
    
    # Sector concentration
    sector_concentration = metrics.get("sector_concentration", 0)
    if sector_concentration > 0.3:
        insights["sector_concentration"] = {
            "status": "high",
            "message": "High sector concentration increases vulnerability to sector-specific risks."
        }
    
    # Cash allocation
    cash_allocation = portfolio.cash_allocation
    if cash_allocation > 20:
        insights["cash"] = {
            "status": "high",
            "message": f"Cash allocation ({cash_allocation:.1f}%) is high, may be missing market opportunities."
        }
    elif cash_allocation < 5:
        insights["cash"] = {
            "status": "low",
            "message": f"Cash allocation ({cash_allocation:.1f}%) is low, consider maintaining a safety buffer."
        }
    
    # Incorporate LLM insights
    parsed_results = llm_analysis.get("parsed_results", {})
    
    # Add LLM-based overall assessment
    if "portfolio_assessment" in parsed_results:
        insights["llm_assessment"] = {
            "message": parsed_results["portfolio_assessment"]
        }
    
    # Add LLM-identified positions needing attention
    if "positions_needing_attention" in parsed_results:
        insights["attention_needed"] = parsed_results["positions_needing_attention"]
    
    return insights