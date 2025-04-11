"""
Tests for the portfolio analysis module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime

from src.schwab.portfolio import Portfolio, Position
from src.analysis.portfolio import analyze_portfolio, calculate_portfolio_metrics
from src.analysis.portfolio import calculate_risk_metrics, parse_llm_analysis, generate_insights


class TestPortfolioAnalysis(unittest.TestCase):
    """Test cases for portfolio analysis."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample positions
        position1 = Position(
            symbol="AAPL",
            quantity=10,
            asset_type="EQUITY",
            cost_basis=150.0,
            market_value=1700.0,
            current_price=170.0,
            instrument_data={"fundamental": {"sector": "Technology", "beta": 1.2}}
        )
        
        position2 = Position(
            symbol="MSFT",
            quantity=5,
            asset_type="EQUITY",
            cost_basis=200.0,
            market_value=1250.0,
            current_price=250.0,
            instrument_data={"fundamental": {"sector": "Technology", "beta": 1.1}}
        )
        
        position3 = Position(
            symbol="JNJ",
            quantity=8,
            asset_type="EQUITY",
            cost_basis=160.0,
            market_value=1280.0,
            current_price=160.0,
            instrument_data={"fundamental": {"sector": "Healthcare", "beta": 0.8}}
        )
        
        # Create sample portfolio
        self.portfolio = Portfolio(
            account_id="test_account",
            positions=[position1, position2, position3],
            account_value=5000.0,
            cash_balance=770.0,
            timestamp=datetime.now()
        )
        
        # Mock LLM client
        self.llm_client = MagicMock()
        self.llm_client.name = "Test LLM"
        self.llm_client.generate.return_value = """
        Portfolio Assessment:
        The portfolio is moderately diversified with a technology sector overweight.
        
        Strengths:
        - Good cash balance for potential opportunities
        - Strong positions in established companies
        
        Vulnerabilities:
        - Technology sector concentration
        - Market risk above average
        
        Positions Needing Attention:
        - AAPL: High concentration relative to portfolio size
        
        Rebalancing Recommendations:
        - Consider reducing tech exposure by 5-10%
        
        Cash Deployment Suggestions:
        - Explore adding a value stock or ETF for diversification
        """
        
        # Mock config
        self.config = {
            "RISK_TOLERANCE": 5,
            "MAX_POSITION_SIZE_PERCENT": 10,
            "MAX_SECTOR_EXPOSURE_PERCENT": 25
        }
        
        # Mock market data client
        self.market_data_client = MagicMock()
        self.market_data_client.get_market_indices.return_value = {
            "S&P 500": {"price": 5000, "change_percent": 0.5},
            "Dow Jones": {"price": 38000, "change_percent": 0.3}
        }
        self.market_data_client.get_sector_performance.return_value = {
            "Technology": {"performance": 0.8},
            "Healthcare": {"performance": 0.2}
        }
    
    def test_calculate_portfolio_metrics(self):
        """Test calculation of portfolio metrics."""
        metrics = calculate_portfolio_metrics(self.portfolio)
        
        # Check that metrics are calculated
        self.assertIn("diversity_score", metrics)
        self.assertIn("concentration_score", metrics)
        self.assertIn("top_holdings", metrics)
        self.assertIn("sector_concentration", metrics)
        
        # Check top holdings
        self.assertEqual(len(metrics["top_holdings"]), 3)  # All positions should be included
        
        # Check that sector data is present
        self.assertIn("sector_data", metrics)
        self.assertEqual(len(metrics["sector_data"]), 2)  # Technology and Healthcare
    
    def test_calculate_risk_metrics(self):
        """Test calculation of risk metrics."""
        risk_metrics = calculate_risk_metrics(self.portfolio)
        
        # Check that risk metrics are calculated
        self.assertIn("beta", risk_metrics)
        self.assertIsNotNone(risk_metrics["beta"])
        
        # Calculate expected portfolio beta
        weights = [p.weight / 100 for p in self.portfolio.positions]
        betas = [1.2, 1.1, 0.8]
        expected_beta = sum(w * b for w, b in zip(weights, betas))
        
        # Check beta calculation (within tolerance)
        self.assertAlmostEqual(risk_metrics["beta"], expected_beta, places=2)
        
        # Check risk concentration
        self.assertIn("risk_concentration", risk_metrics)
        
    def test_parse_llm_analysis(self):
        """Test parsing of LLM analysis text."""
        analysis_text = self.llm_client.generate.return_value
        
        parsed_results = parse_llm_analysis(analysis_text)
        
        # Check that sections are extracted
        self.assertIn("portfolio_assessment", parsed_results)
        self.assertIn("strengths", parsed_results)
        self.assertIn("vulnerabilities", parsed_results)
        self.assertIn("positions_needing_attention", parsed_results)
        self.assertIn("rebalancing_recommendations", parsed_results)
        self.assertIn("cash_deployment_suggestions", parsed_results)
        
        # Check that positions needing attention are structured correctly
        positions = parsed_results["positions_needing_attention"]
        self.assertTrue(isinstance(positions, list))
        if positions:
            position = positions[0]
            self.assertEqual(position["symbol"], "AAPL")
    
    def test_generate_insights(self):
        """Test generation of portfolio insights."""
        # Mock input data
        metrics = {
            "diversity_score": 0.6,
            "concentration_score": 0.4,
            "sector_concentration": 0.3
        }
        
        risk_metrics = {
            "beta": 1.1,
            "risk_concentration": 35.0
        }
        
        llm_analysis = {
            "parsed_results": {
                "portfolio_assessment": "The portfolio is moderately diversified.",
                "positions_needing_attention": [{"symbol": "AAPL", "reason": "High concentration"}]
            }
        }
        
        # Generate insights
        insights = generate_insights(self.portfolio, metrics, risk_metrics, llm_analysis)
        
        # Check that insights are generated
        self.assertIn("diversity", insights)
        self.assertIn("risk", insights)
        self.assertIn("sector_concentration", insights)
        
        # Check that LLM insights are included
        self.assertIn("llm_assessment", insights)
        self.assertIn("attention_needed", insights)
    
    @patch('src.analysis.portfolio.get_market_data')
    def test_analyze_portfolio(self, mock_get_market_data):
        """Test full portfolio analysis."""
        # Set up mock market data
        mock_get_market_data.return_value = {
            "indices": {
                "S&P 500": {"current": 5000, "change_percent": 0.5},
                "Dow Jones": {"current": 38000, "change_percent": 0.3}
            },
            "sector_performance": {
                "Technology": {"performance": 0.8},
                "Healthcare": {"performance": 0.2}
            },
            "economic_indicators": {
                "VIX": 15.0
            }
        }
        
        # Call analyze_portfolio
        result = analyze_portfolio(
            self.portfolio, 
            self.llm_client, 
            self.market_data_client,
            self.config
        )
        
        # Check that all expected sections are present
        self.assertIn("timestamp", result)
        self.assertIn("account_id", result)
        self.assertIn("metrics", result)
        self.assertIn("insights", result)
        self.assertIn("risk_metrics", result)
        self.assertIn("llm_analysis", result)
        
        # Check that LLM was called with expected arguments
        self.llm_client.generate.assert_called_once()
        
        # Check that insights were generated
        self.assertTrue(len(result["insights"]) > 0)


if __name__ == '__main__':
    unittest.main()