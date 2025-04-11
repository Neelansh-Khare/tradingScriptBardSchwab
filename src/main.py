#!/usr/bin/env python
"""
Schwab-AI Portfolio Manager

A Python application that automatically connects to your Charles Schwab account 
via the schwab-py library and uses AI/LLM APIs to analyze and manage your
portfolio with a risk-averse approach.
"""

import argparse
import os
import sys
import logging
from pathlib import Path

# Add the src directory to the path so we can import our modules
src_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(src_dir.parent))

from src.utils.config import load_config
from src.utils.logging import setup_logging
from src.schwab.auth import authenticate_schwab
from src.schwab.client import SchwabClient
from src.llm.client import get_llm_client
from src.data.market_data import MarketDataClient
from src.analysis.portfolio import analyze_portfolio
from src.analysis.recommendation import generate_recommendations
from src.trading.executor import execute_trades
from src.utils.reporting import generate_report


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Schwab-AI Portfolio Manager: AI-powered trading with risk-averse algorithms"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=".env",
        help="Path to the configuration file (default: .env)",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze portfolio without making trades",
    )
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate a detailed report of your portfolio",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run (no actual trades)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    return parser.parse_args()


def main():
    """Main application entry point."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up logging
    setup_logging(level=getattr(logging, args.log_level))
    logger = logging.getLogger(__name__)
    logger.info("Starting Schwab-AI Portfolio Manager")
    
    try:
        # Load configuration
        config = load_config(args.config)
        logger.info("Configuration loaded successfully")
        
        # Override config with command-line arguments
        if args.dry_run:
            config["DRY_RUN"] = True
            logger.info("Dry run mode enabled via command line")
        
        # Authenticate with Schwab API
        schwab_client = authenticate_schwab(config)
        logger.info("Successfully authenticated with Schwab API")
        
        # Initialize LLM client
        llm_client = get_llm_client(config)
        logger.info(f"Initialized {llm_client.name} LLM client")
        
        # Initialize market data client
        market_data_client = MarketDataClient(config)
        logger.info(f"Initialized market data client with default provider: {market_data_client.default_provider}")
        
        # Retrieve account and portfolio information
        portfolio = schwab_client.get_portfolio()
        logger.info(f"Retrieved portfolio with {len(portfolio.positions)} positions")
        
        # Get real-time quotes for portfolio holdings
        if portfolio.positions:
            symbols = [p.symbol for p in portfolio.positions]
            try:
                quotes = market_data_client.get_multiple_quotes(symbols)
                logger.info(f"Retrieved real-time quotes for {len(quotes)} positions")
                
                # Update portfolio with real-time data
                for position in portfolio.positions:
                    if position.symbol in quotes:
                        quote = quotes[position.symbol]
                        position.current_price = quote["price"]
                        position.market_value = position.quantity * position.current_price
                
                # Recalculate portfolio metrics
                portfolio._calculate_position_weights()
                logger.info("Updated portfolio with real-time prices")
            except Exception as e:
                logger.warning(f"Failed to update portfolio with real-time data: {str(e)}")
        
        # Analyze portfolio
        analysis_results = analyze_portfolio(portfolio, llm_client, market_data_client, config)
        logger.info("Portfolio analysis completed")
        
        # Generate a report if requested
        if args.generate_report:
            report_path = generate_report(portfolio, analysis_results, config)
            logger.info(f"Report generated and saved to {report_path}")
            
        # Stop here if analyze-only is specified
        if args.analyze_only:
            logger.info("Analysis complete. Stopping as --analyze-only was specified")
            return
        
        # Generate trade recommendations
        recommendations = generate_recommendations(portfolio, analysis_results, config)
        logger.info(f"Generated {len(recommendations)} trade recommendations")
        
        # Execute trades
        if config.get("ENABLE_AUTO_TRADING", False):
            executed_trades = execute_trades(recommendations, schwab_client, config)
            logger.info(f"Executed {len(executed_trades)} trades")
        else:
            logger.info("Auto-trading is disabled. No trades were executed")
            
        logger.info("Schwab-AI Portfolio Manager completed successfully")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()