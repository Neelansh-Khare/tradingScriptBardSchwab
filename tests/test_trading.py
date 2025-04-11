"""
Tests for the trading module.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

from src.schwab.portfolio import Portfolio, Position
from src.analysis.recommendation import Recommendation
from src.trading.validation import validate_trade, validate_symbol, validate_quantity
from src.trading.validation import validate_buy, validate_sell
from src.trading.executor import execute_trades, execute_single_trade, ExecutedTrade
from src.trading.strategy import RiskAverseStrategy


class TestTradeValidation(unittest.TestCase):
    """Test cases for trade validation."""
    
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
        
        # Create sample portfolio
        self.portfolio = Portfolio(
            account_id="test_account",
            positions=[position1, position2],
            account_value=5000.0,
            cash_balance=2050.0,
            timestamp=datetime.now()
        )
        
        # Mock Schwab client
        self.client = MagicMock()
        self.client.get_portfolio.return_value = self.portfolio
        
        # Set up quotes response
        quotes_response = {
            "AAPL": {"lastPrice": 170.0},
            "MSFT": {"lastPrice": 250.0},
            "VTI": {"lastPrice": 220.0}
        }
        self.client.get_quote.return_value = quotes_response
        
        # Sample recommendations
        self.buy_rec = Recommendation(
            action="BUY",
            symbol="VTI",
            quantity=5,
            rationale="Diversification"
        )
        
        self.sell_rec = Recommendation(
            action="SELL",
            symbol="AAPL",
            percentage=30,
            rationale="Reduce concentration"
        )
        
        # Mock config
        self.config = {
            "RISK_TOLERANCE": 5,
            "MAX_POSITION_SIZE_PERCENT": 25,
            "MAX_SECTOR_EXPOSURE_PERCENT": 40,
            "MIN_CASH_RESERVE_PERCENT": 5,
            "DRY_RUN": True,
            "ENABLE_AUTO_TRADING": True,
            "MAX_TRADES_PER_SESSION": 3
        }
    
    @patch('src.trading.validation.validate_symbol')
    def test_validate_trade(self, mock_validate_symbol):
        """Test trade validation."""
        # Configure mocks
        mock_validate_symbol.return_value = True
        
        # Buy validation
        with patch('src.trading.validation.validate_quantity') as mock_validate_quantity, \
             patch('src.trading.validation.validate_buy') as mock_validate_buy:
            
            mock_validate_quantity.return_value = {"valid": True, "quantity": 5}
            mock_validate_buy.return_value = {"valid": True}
            
            result = validate_trade(self.buy_rec, self.client, self.config)
            
            self.assertTrue(result["valid"])
            self.assertEqual(result["quantity"], 5)
            
            # Check that all validation steps were called
            mock_validate_symbol.assert_called_once_with("VTI", self.client)
            mock_validate_quantity.assert_called_once()
            mock_validate_buy.assert_called_once()
        
        # Sell validation
        with patch('src.trading.validation.validate_quantity') as mock_validate_quantity, \
             patch('src.trading.validation.validate_sell') as mock_validate_sell:
            
            mock_validate_quantity.return_value = {"valid": True, "quantity": 3}
            mock_validate_sell.return_value = {"valid": True}
            
            result = validate_trade(self.sell_rec, self.client, self.config)
            
            self.assertTrue(result["valid"])
            self.assertEqual(result["quantity"], 3)
            
            # Check that all validation steps were called
            mock_validate_sell.assert_called_once()
    
    def test_validate_symbol(self):
        """Test symbol validation."""
        # Set up client mock
        self.client.get_quote.return_value = {"AAPL": {}}
        
        # Valid symbol
        result = validate_symbol("AAPL", self.client)
        self.assertTrue(result)
        
        # Invalid symbol
        self.client.get_quote.return_value = {}
        result = validate_symbol("INVALID", self.client)
        self.assertFalse(result)
        
        # Exception case
        self.client.get_quote.side_effect = Exception("API Error")
        result = validate_symbol("AAPL", self.client)
        self.assertFalse(result)
    
    def test_validate_quantity(self):
        """Test quantity validation."""
        position = self.portfolio.get_position_by_symbol("AAPL")
        
        # Test with direct quantity (buy)
        result = validate_quantity(
            self.buy_rec, None, self.portfolio, 220.0, self.config
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["quantity"], 5)
        
        # Test with percentage (sell)
        result = validate_quantity(
            self.sell_rec, position, self.portfolio, 170.0, self.config
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["quantity"], 3)  # 30% of 10 shares
        
        # Test sell without position
        invalid_sell = Recommendation(
            action="SELL",
            symbol="INVALID",
            quantity=5,
            rationale="Test"
        )
        result = validate_quantity(
            invalid_sell, None, self.portfolio, 100.0, self.config
        )
        self.assertFalse(result["valid"])
        
        # Test buy with insufficient cash
        expensive_buy = Recommendation(
            action="BUY",
            symbol="VTI",
            quantity=100,
            rationale="Test"
        )
        result = validate_quantity(
            expensive_buy, None, self.portfolio, 220.0, self.config
        )
        self.assertFalse(result["valid"])
    
    def test_validate_buy(self):
        """Test buy validation."""
        # Normal buy within limits
        result = validate_buy(
            self.buy_rec, self.portfolio, 5, 220.0, self.config
        )
        self.assertTrue(result["valid"])
        
        # Buy with insufficient cash
        result = validate_buy(
            self.buy_rec, self.portfolio, 50, 220.0, self.config
        )
        self.assertFalse(result["valid"])
        self.assertIn("Insufficient cash", result["reason"])
        
        # Buy that would exceed position limit
        big_buy = Recommendation(
            action="BUY",
            symbol="MSFT",
            quantity=10,
            rationale="Test"
        )
        result = validate_buy(
            big_buy, self.portfolio, 10, 250.0, self.config
        )
        self.assertFalse(result["valid"])
        self.assertIn("maximum size", result["reason"])
    
    def test_validate_sell(self):
        """Test sell validation."""
        position = self.portfolio.get_position_by_symbol("AAPL")
        
        # Normal sell within limits
        result = validate_sell(
            self.sell_rec, position, 3, self.config
        )
        self.assertTrue(result["valid"])
        
        # Sell non-existent position
        result = validate_sell(
            Recommendation(action="SELL", symbol="INVALID", quantity=5),
            None, 5, self.config
        )
        self.assertFalse(result["valid"])
        self.assertIn("non-existent position", result["reason"])
        
        # Sell too many shares
        result = validate_sell(
            Recommendation(action="SELL", symbol="AAPL", quantity=20),
            position, 20, self.config
        )
        self.assertFalse(result["valid"])
        self.assertIn("Insufficient shares", result["reason"])


class TestTradeExecution(unittest.TestCase):
    """Test cases for trade execution."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create recommendations
        self.recommendations = [
            Recommendation(action="BUY", symbol="VTI", quantity=5, rationale="Diversification"),
            Recommendation(action="SELL", symbol="AAPL", percentage=30, rationale="Reduce concentration")
        ]
        self.recommendations[0].priority = 5
        self.recommendations[1].priority = 8
        
        # Mock Schwab client
        self.client = MagicMock()
        
        # Mock config
        self.config = {
            "DRY_RUN": True,
            "ENABLE_AUTO_TRADING": True,
            "MAX_TRADES_PER_SESSION": 3
        }
    
    @patch('src.trading.executor.validate_trade')
    @patch('src.trading.executor.execute_single_trade')
    def test_execute_trades(self, mock_execute_single_trade, mock_validate_trade):
        """Test trade execution."""
        # Configure mocks
        mock_validate_trade.return_value = {"valid": True, "quantity": 5}
        mock_execute_single_trade.return_value = ExecutedTrade(
            symbol="VTI", action="BUY", quantity=5, status="simulated"
        )
        
        # Execute trades
        executed_trades = execute_trades(self.recommendations, self.client, self.config)
        
        # Check that validation and execution were called for each recommendation
        self.assertEqual(mock_validate_trade.call_count, 2)
        self.assertEqual(mock_execute_single_trade.call_count, 2)
        
        # Check that executed trades are returned
        self.assertEqual(len(executed_trades), 2)
        self.assertEqual(executed_trades[0].symbol, "AAPL")  # Higher priority should be first
        self.assertEqual(executed_trades[1].symbol, "VTI")
        
        # Test with disabled auto-trading
        self.config["ENABLE_AUTO_TRADING"] = False
        executed_trades = execute_trades(self.recommendations, self.client, self.config)
        self.assertEqual(len(executed_trades), 0)
        
        # Test with validation failures
        mock_validate_trade.return_value = {"valid": False, "reason": "Test failure"}
        self.config["ENABLE_AUTO_TRADING"] = True
        executed_trades = execute_trades(self.recommendations, self.client, self.config)
        self.assertEqual(len(executed_trades), 0)
    
    def test_execute_single_trade(self):
        """Test single trade execution."""
        # Configure mock
        self.client.create_equity_order.return_value = {"orderId": "test_order_id"}
        
        # Execute buy
        executed_trade = execute_single_trade(
            self.recommendations[0], 5, self.client, None, True
        )
        
        # Check that client.create_equity_order was called
        self.client.create_equity_order.assert_called_once_with(
            symbol="VTI",
            quantity=5,
            instruction="BUY",
            price=None,
            dry_run=True
        )
        
        # Check executed trade
        self.assertEqual(executed_trade.symbol, "VTI")
        self.assertEqual(executed_trade.action, "BUY")
        self.assertEqual(executed_trade.quantity, 5)
        self.assertEqual(executed_trade.status, "simulated")
        
        # Test with exception
        self.client.create_equity_order.side_effect = Exception("API Error")
        with self.assertRaises(Exception):
            execute_single_trade(self.recommendations[0], 5, self.client, None, True)


class TestTradingStrategy(unittest.TestCase):
    """Test cases for trading strategies."""
    
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
        
        # Create sample portfolio
        self.portfolio = Portfolio(
            account_id="test_account",
            positions=[position1, position2],
            account_value=5000.0,
            cash_balance=2050.0,
            timestamp=datetime.now()
        )
        
        # Analysis results
        self.analysis_results = {
            "risk_metrics": {
                "position_risks": [
                    {"symbol": "AAPL", "risk_score": 75.0, "weight": 34.0, "beta": 1.2},
                    {"symbol": "MSFT", "risk_score": 65.0, "weight": 25.0, "beta": 1.1}
                ]
            },
            "metrics": {
                "diversity_score": 0.6,
                "concentration_score": 0.4,
                "sector_concentration": 0.3
            }
        }
        
        # Config
        self.config = {
            "RISK_TOLERANCE": 3,
            "MAX_POSITION_SIZE_PERCENT": 25.0,
            "MAX_SECTOR_EXPOSURE_PERCENT": 40.0
        }
    
    def test_risk_averse_strategy(self):
        """Test the risk-averse trading strategy."""
        strategy = RiskAverseStrategy(self.config)
        
        # Generate recommendations
        recommendations = strategy.generate_recommendations(
            self.portfolio, self.analysis_results
        )
        
        # Check that recommendations were generated
        self.assertTrue(len(recommendations) > 0)
        
        # Check for position size recommendations
        position_size_recs = [r for r in recommendations 
                             if "exceed" in r.rationale.lower() and 
                             "maximum size" in r.rationale.lower()]
        self.assertTrue(len(position_size_recs) > 0)
        
        # Check that recommendations are sorted by priority
        priorities = [r.priority for r in recommendations]
        self.assertEqual(priorities, sorted(priorities, reverse=True))
        
        # Test with empty portfolio
        empty_portfolio = Portfolio(
            account_id="test_account",
            positions=[],
            account_value=1000.0,
            cash_balance=1000.0,
            timestamp=datetime.now()
        )
        
        recommendations = strategy.generate_recommendations(
            empty_portfolio, {"risk_metrics": {}, "metrics": {}}
        )
        
        # Should get cash deployment recommendation
        self.assertTrue(len(recommendations) > 0)
        self.assertTrue(any("cash" in r.rationale.lower() for r in recommendations))


if __name__ == '__main__':
    unittest.main()