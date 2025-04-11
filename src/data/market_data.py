"""
Real-time market data module for the Schwab-AI Portfolio Manager.

This module handles fetching and processing real-time market data
from various providers.
"""

import logging
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataError(Exception):
    """Exception raised for market data errors."""
    pass


class MarketDataClient:
    """
    Client for fetching real-time market data.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the market data client.
        
        Args:
            config (dict): Configuration dictionary.
        """
        self.config = config
        
        # Set up API keys
        self.alpha_vantage_api_key = config.get("ALPHA_VANTAGE_API_KEY")
        self.finnhub_api_key = config.get("FINNHUB_API_KEY")
        self.polygon_api_key = config.get("POLYGON_API_KEY")
        
        # Set default provider
        if self.alpha_vantage_api_key:
            self.default_provider = "alpha_vantage"
        elif self.finnhub_api_key:
            self.default_provider = "finnhub"
        elif self.polygon_api_key:
            self.default_provider = "polygon"
        else:
            self.default_provider = "yfinance"
            
        logger.info(f"Initialized market data client with default provider: {self.default_provider}")
    
    def get_quote(self, symbol: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a real-time quote for a symbol.
        
        Args:
            symbol (str): The symbol to get a quote for.
            provider (str, optional): The data provider to use.
                                     If None, uses default provider.
                                     
        Returns:
            Dict[str, Any]: Quote data.
            
        Raises:
            MarketDataError: If the quote fetch fails.
        """
        provider = provider or self.default_provider
        
        try:
            # Use the appropriate provider
            if provider == "alpha_vantage":
                return self._get_alpha_vantage_quote(symbol)
            elif provider == "finnhub":
                return self._get_finnhub_quote(symbol)
            elif provider == "polygon":
                return self._get_polygon_quote(symbol)
            else:
                return self._get_yfinance_quote(symbol)
                
        except Exception as e:
            error_msg = f"Failed to get quote for {symbol}: {str(e)}"
            logger.error(error_msg)
            
            # Try fallback to YFinance if another provider failed
            if provider != "yfinance":
                logger.info(f"Falling back to YFinance for {symbol}")
                try:
                    return self._get_yfinance_quote(symbol)
                except Exception as fallback_error:
                    raise MarketDataError(f"Fallback to YFinance also failed: {str(fallback_error)}") from fallback_error
            else:
                raise MarketDataError(error_msg) from e
    
    def _get_alpha_vantage_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get a quote from Alpha Vantage.
        
        Args:
            symbol (str): The symbol to get a quote for.
            
        Returns:
            Dict[str, Any]: Quote data.
            
        Raises:
            MarketDataError: If the quote fetch fails.
        """
        if not self.alpha_vantage_api_key:
            raise MarketDataError("Alpha Vantage API key not configured")
            
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.alpha_vantage_api_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "Global Quote" not in data or not data["Global Quote"]:
                raise MarketDataError(f"No quote data found for {symbol}")
                
            quote_data = data["Global Quote"]
            
            return {
                "symbol": symbol,
                "price": float(quote_data.get("05. price", 0)),
                "change": float(quote_data.get("09. change", 0)),
                "change_percent": float(quote_data.get("10. change percent", "0%").replace("%", "")),
                "volume": int(quote_data.get("06. volume", 0)),
                "timestamp": datetime.now().isoformat(),
                "provider": "alpha_vantage"
            }
            
        except Exception as e:
            error_msg = f"Alpha Vantage quote fetch failed: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e
    
    def _get_finnhub_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get a quote from Finnhub.
        
        Args:
            symbol (str): The symbol to get a quote for.
            
        Returns:
            Dict[str, Any]: Quote data.
            
        Raises:
            MarketDataError: If the quote fetch fails.
        """
        if not self.finnhub_api_key:
            raise MarketDataError("Finnhub API key not configured")
            
        try:
            url = f"https://finnhub.io/api/v1/quote"
            params = {
                "symbol": symbol,
                "token": self.finnhub_api_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data or "c" not in data:
                raise MarketDataError(f"No quote data found for {symbol}")
                
            price = data.get("c", 0)
            prev_close = data.get("pc", 0)
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            
            return {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "volume": data.get("v", 0),
                "timestamp": datetime.fromtimestamp(data.get("t", time.time())).isoformat(),
                "provider": "finnhub"
            }
            
        except Exception as e:
            error_msg = f"Finnhub quote fetch failed: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e
    
    def _get_polygon_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get a quote from Polygon.io.
        
        Args:
            symbol (str): The symbol to get a quote for.
            
        Returns:
            Dict[str, Any]: Quote data.
            
        Raises:
            MarketDataError: If the quote fetch fails.
        """
        if not self.polygon_api_key:
            raise MarketDataError("Polygon API key not configured")
            
        try:
            url = f"https://api.polygon.io/v2/last/trade/{symbol}"
            params = {
                "apiKey": self.polygon_api_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data or "results" not in data:
                raise MarketDataError(f"No quote data found for {symbol}")
                
            trade = data.get("results", {})
            price = trade.get("p", 0)
            
            # Get previous close for change calculation
            yesterday = datetime.now() - timedelta(days=1)
            prev_url = f"https://api.polygon.io/v1/open-close/{symbol}/{yesterday.strftime('%Y-%m-%d')}"
            
            prev_response = requests.get(prev_url, params=params)
            prev_data = prev_response.json() if prev_response.status_code == 200 else {}
            
            prev_close = prev_data.get("close", price)  # Fall back to current price if prev not available
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            
            return {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "volume": trade.get("s", 0),  # Size of trade
                "timestamp": datetime.fromtimestamp(trade.get("t", time.time()) / 1000).isoformat(),
                "provider": "polygon"
            }
            
        except Exception as e:
            error_msg = f"Polygon quote fetch failed: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e
    
    def _get_yfinance_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get a quote from Yahoo Finance (yfinance).
        
        Args:
            symbol (str): The symbol to get a quote for.
            
        Returns:
            Dict[str, Any]: Quote data.
            
        Raises:
            MarketDataError: If the quote fetch fails.
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Get quote data
            data = ticker.history(period="2d")
            
            if data.empty:
                raise MarketDataError(f"No data found for {symbol}")
                
            # Get the last row
            latest = data.iloc[-1]
            
            # Get the previous day for change calculation
            prev_close = data.iloc[-2]["Close"] if len(data) > 1 else latest["Open"]
            
            price = latest["Close"]
            change = price - prev_close
            change_percent = (change / prev_close * 100) if prev_close > 0 else 0
            
            return {
                "symbol": symbol,
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "volume": latest["Volume"],
                "timestamp": data.index[-1].isoformat(),
                "provider": "yfinance"
            }
            
        except Exception as e:
            error_msg = f"YFinance quote fetch failed: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e
    
    def get_historical_data(self, symbol: str, period: str = "1y", 
                           interval: str = "1d") -> pd.DataFrame:
        """
        Get historical price data for a symbol.
        
        Args:
            symbol (str): The symbol to get data for.
            period (str): The time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max').
            interval (str): The data interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo').
            
        Returns:
            pd.DataFrame: Historical price data.
            
        Raises:
            MarketDataError: If the data fetch fails.
        """
        try:
            # Use yfinance for historical data (most reliable free option)
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                raise MarketDataError(f"No historical data found for {symbol}")
                
            return data
            
        except Exception as e:
            error_msg = f"Failed to get historical data for {symbol}: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e
    
    def get_multiple_quotes(self, symbols: List[str], 
                          provider: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get quotes for multiple symbols.
        
        Args:
            symbols (List[str]): The symbols to get quotes for.
            provider (str, optional): The data provider to use.
            
        Returns:
            Dict[str, Dict[str, Any]]: Quote data keyed by symbol.
            
        Raises:
            MarketDataError: If the quote fetch fails.
        """
        results = {}
        errors = []
        
        for symbol in symbols:
            try:
                quote = self.get_quote(symbol, provider)
                results[symbol] = quote
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                
        if errors and len(errors) == len(symbols):
            # All quotes failed
            raise MarketDataError(f"Failed to get any quotes: {'; '.join(errors)}")
            
        return results
    
    def get_market_indices(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current values for major market indices.
        
        Returns:
            Dict[str, Dict[str, Any]]: Index data keyed by index symbol.
            
        Raises:
            MarketDataError: If the data fetch fails.
        """
        # Major US indices
        indices = ["^GSPC", "^DJI", "^IXIC", "^RUT"]  # S&P 500, Dow, Nasdaq, Russell 2000
        
        try:
            # Get quotes for indices
            quotes = self.get_multiple_quotes(indices)
            
            # Format the results
            result = {
                "S&P 500": quotes.get("^GSPC", {}),
                "Dow Jones": quotes.get("^DJI", {}),
                "Nasdaq": quotes.get("^IXIC", {}),
                "Russell 2000": quotes.get("^RUT", {})
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to get market indices: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e
    
    def get_sector_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance data for market sectors.
        
        Returns:
            Dict[str, Dict[str, Any]]: Sector performance data.
            
        Raises:
            MarketDataError: If the data fetch fails.
        """
        # Sector ETFs
        sector_etfs = {
            "Technology": "XLK",
            "Healthcare": "XLV",
            "Financials": "XLF",
            "Consumer Discretionary": "XLY",
            "Industrials": "XLI",
            "Energy": "XLE",
            "Materials": "XLB",
            "Utilities": "XLU",
            "Real Estate": "XLRE",
            "Consumer Staples": "XLP",
            "Communication Services": "XLC"
        }
        
        try:
            # Get quotes for sector ETFs
            etf_quotes = self.get_multiple_quotes(list(sector_etfs.values()))
            
            # Format the results
            result = {}
            for sector, etf in sector_etfs.items():
                if etf in etf_quotes:
                    result[sector] = {
                        "performance": etf_quotes[etf].get("change_percent", 0),
                        "price": etf_quotes[etf].get("price", 0),
                        "symbol": etf
                    }
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to get sector performance: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e
    
    def get_stock_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent news for a stock.
        
        Args:
            symbol (str): The stock symbol.
            limit (int): Maximum number of news items to return.
            
        Returns:
            List[Dict[str, Any]]: News data.
            
        Raises:
            MarketDataError: If the news fetch fails.
        """
        if self.finnhub_api_key:
            return self._get_finnhub_news(symbol, limit)
        else:
            # Use Yahoo Finance as fallback
            return self._get_yfinance_news(symbol, limit)
    
    def _get_finnhub_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get news from Finnhub.
        
        Args:
            symbol (str): The stock symbol.
            limit (int): Maximum number of news items to return.
            
        Returns:
            List[Dict[str, Any]]: News data.
            
        Raises:
            MarketDataError: If the news fetch fails.
        """
        try:
            url = "https://finnhub.io/api/v1/company-news"
            
            # Get news for the last 7 days
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            params = {
                "symbol": symbol,
                "from": start_date,
                "to": end_date,
                "token": self.finnhub_api_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Process the data
            news_items = []
            for item in data[:limit]:
                news_items.append({
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", ""),
                    "date": datetime.fromtimestamp(item.get("datetime", 0)).isoformat(),
                    "sentiment": "unknown"  # Finnhub doesn't provide sentiment
                })
                
            return news_items
            
        except Exception as e:
            error_msg = f"Finnhub news fetch failed: {str(e)}"
            logger.error(error_msg)
            
            # Fall back to Yahoo Finance
            return self._get_yfinance_news(symbol, limit)
    
    def _get_yfinance_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get news from Yahoo Finance.
        
        Args:
            symbol (str): The stock symbol.
            limit (int): Maximum number of news items to return.
            
        Returns:
            List[Dict[str, Any]]: News data.
            
        Raises:
            MarketDataError: If the news fetch fails.
        """
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            # Process the data
            news_items = []
            for item in news[:limit]:
                news_items.append({
                    "headline": item.get("title", ""),
                    "summary": "",  # Yahoo Finance doesn't provide summaries
                    "url": item.get("link", ""),
                    "source": item.get("publisher", ""),
                    "date": datetime.fromtimestamp(item.get("providerPublishTime", 0)).isoformat(),
                    "sentiment": "unknown"  # Yahoo Finance doesn't provide sentiment
                })
                
            return news_items
            
        except Exception as e:
            error_msg = f"YFinance news fetch failed: {str(e)}"
            logger.error(error_msg)
            raise MarketDataError(error_msg) from e