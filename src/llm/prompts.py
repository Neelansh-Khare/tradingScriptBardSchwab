"""
LLM prompt templates for the Schwab-AI Portfolio Manager.

This module provides prompt templates for various LLM tasks.
"""

from typing import Dict, Any, List


class PromptTemplates:
    """
    Collection of prompt templates for LLM analysis.
    """
    
    @staticmethod
    def portfolio_analysis(portfolio_data: Dict[str, Any], 
                           market_data: Dict[str, Any],
                           risk_profile: Dict[str, Any]) -> str:
        """
        Create a prompt for portfolio analysis.
        
        Args:
            portfolio_data (dict): Portfolio data and metrics.
            market_data (dict): Market data and indices.
            risk_profile (dict): User's risk profile preferences.
            
        Returns:
            str: Formatted prompt.
        """
        # Format portfolio holdings
        holdings_text = "Portfolio Holdings:\n"
        for position in portfolio_data.get("positions", []):
            holdings_text += (
                f"- {position['symbol']}: {position['quantity']} shares, "
                f"Current Price: ${position['current_price']:.2f}, "
                f"Market Value: ${position['market_value']:.2f}, "
                f"Weight: {position['weight']:.2f}%, "
                f"Unrealized P/L: ${position['unrealized_pl']:.2f} ({position['unrealized_pl_percent']:.2f}%)\n"
            )
            
        # Format sector allocations
        sectors_text = "Sector Allocations:\n"
        for sector, allocation in portfolio_data.get("sector_allocations", {}).items():
            sectors_text += f"- {sector}: {allocation:.2f}%\n"
            
        # Format market data
        market_text = "Market Data:\n"
        for index, data in market_data.get("indices", {}).items():
            market_text += f"- {index}: {data['current']:.2f} ({data['change_percent']:.2f}%)\n"
            
        # Format risk profile
        risk_text = "Risk Profile:\n"
        risk_text += f"- Risk Tolerance: {risk_profile.get('risk_tolerance', 'Unknown')}/10\n"
        risk_text += f"- Max Position Size: {risk_profile.get('max_position_size_percent', 'Unknown')}%\n"
        risk_text += f"- Max Sector Exposure: {risk_profile.get('max_sector_exposure_percent', 'Unknown')}%\n"
        
        # Construct the full prompt
        prompt = f"""
        Analyze the following portfolio and provide insights on its composition, risk, and potential improvements.

        {holdings_text}
        
        {sectors_text}
        
        {market_text}
        
        {risk_text}
        
        Overall Portfolio Metrics:
        - Total Market Value: ${portfolio_data.get('total_market_value', 0):.2f}
        - Cash Balance: ${portfolio_data.get('cash_balance', 0):.2f} ({portfolio_data.get('cash_allocation', 0):.2f}%)
        - Total Unrealized P/L: ${portfolio_data.get('total_unrealized_pl', 0):.2f} ({portfolio_data.get('total_unrealized_pl_percent', 0):.2f}%)
        
        Please analyze this portfolio and provide:
        
        1. Overall portfolio assessment (diversification, sector balance, risk level)
        2. Key strengths and vulnerabilities
        3. Positions that may need attention (overweight, underperforming, high risk)
        4. Recommendations for rebalancing or risk reduction
        5. Suggestions for capital deployment (for available cash)
        
        Focus on a risk-averse approach that prioritizes capital preservation while still seeking reasonable returns.
        """
        
        return prompt
    
    @staticmethod
    def stock_analysis(symbol: str, 
                      stock_data: Dict[str, Any],
                      news_data: List[Dict[str, Any]],
                      market_context: Dict[str, Any],
                      historical_data: Optional[pd.DataFrame] = None) -> str:
        """
        Create a prompt for individual stock analysis.
        
        Args:
            symbol (str): The stock symbol.
            stock_data (dict): Stock data and metrics.
            news_data (list): Recent news articles about the stock.
            market_context (dict): Broader market context.
            historical_data (pd.DataFrame, optional): Historical price data.
            
        Returns:
            str: Formatted prompt.
        """
        # Format stock data
        stock_text = f"Stock Data for {symbol}:\n"
        stock_text += f"- Current Price: ${stock_data.get('price', 0):.2f}\n"
        stock_text += f"- 52-Week Range: ${stock_data.get('low_52week', 0):.2f} - ${stock_data.get('high_52week', 0):.2f}\n"
        stock_text += f"- P/E Ratio: {stock_data.get('pe_ratio', 'N/A')}\n"
        stock_text += f"- Market Cap: ${stock_data.get('market_cap', 0) / 1e9:.2f}B\n"
        stock_text += f"- Dividend Yield: {stock_data.get('dividend_yield', 0):.2f}%\n"
        stock_text += f"- Beta: {stock_data.get('beta', 'N/A')}\n"
        
        # Format news data
        news_text = f"Recent News for {symbol}:\n"
        for article in news_data:
            news_text += f"- {article.get('date')}: {article.get('headline')}\n"
            if article.get('summary'):
                news_text += f"  Summary: {article.get('summary')}\n"
                
        # Format market context
        market_text = "Market Context:\n"
        for index, data in market_context.get("indices", {}).items():
            market_text += f"- {index}: {data['current']:.2f} ({data['change_percent']:.2f}%)\n"
            
        # Sector performance
        if "sector_performance" in market_context:
            sector = stock_data.get("sector", "Unknown")
            sector_perf = market_context.get("sector_performance", {}).get(sector, {"performance": 0})
            market_text += f"- {sector} Sector Performance: {sector_perf.get('performance', 0):.2f}%\n"
        
        # Construct the full prompt
        prompt = f"""
        Analyze {symbol} from a risk-averse investor's perspective and provide a comprehensive assessment.

        {stock_text}
        
        {news_text}
        
        {market_text}
        
        Please provide the following analysis:
        
        1. Overall risk assessment for {symbol} (low, medium, high)
        2. Key strengths and vulnerabilities
        3. Potential impact of recent news on stock performance
        4. How this stock compares to its sector and the broader market
        5. Recommendation (strong buy, buy, hold, sell, strong sell) for a risk-averse investor
        6. Specific factors a risk-averse investor should monitor
        
        Focus on long-term stability, risk factors, and capital preservation in your analysis.
        """
        
        return prompt
    
    @staticmethod
    def generate_recommendations(portfolio_data: Dict[str, Any],
                               analysis_results: Dict[str, Any],
                               risk_profile: Dict[str, Any]) -> str:
        """
        Create a prompt to generate trade recommendations.
        
        Args:
            portfolio_data (dict): Portfolio data and metrics.
            analysis_results (dict): Previous analysis results.
            risk_profile (dict): User's risk profile preferences.
            
        Returns:
            str: Formatted prompt.
        """
        # Format portfolio summary
        portfolio_text = "Portfolio Summary:\n"
        portfolio_text += f"- Total Market Value: ${portfolio_data.get('total_market_value', 0):.2f}\n"
        portfolio_text += f"- Cash Balance: ${portfolio_data.get('cash_balance', 0):.2f} ({portfolio_data.get('cash_allocation', 0):.2f}%)\n"
        portfolio_text += f"- Number of Positions: {len(portfolio_data.get('positions', []))}\n"
        
        # Format current allocations
        allocations_text = "Current Allocations:\n"
        for position in portfolio_data.get("positions", [])[:10]:  # Top 10 for brevity
            allocations_text += f"- {position['symbol']}: {position['weight']:.2f}%\n"
            
        # Include sector allocations
        sectors_text = "Sector Allocations:\n"
        for sector, allocation in portfolio_data.get("sector_allocations", {}).items():
            sectors_text += f"- {sector}: {allocation:.2f}%\n"
            
        # Format analysis summary
        analysis_text = "Analysis Summary:\n"
        if "portfolio_assessment" in analysis_results:
            analysis_text += f"Portfolio Assessment: {analysis_results.get('portfolio_assessment')}\n\n"
            
        if "positions_needing_attention" in analysis_results:
            analysis_text += "Positions Needing Attention:\n"
            for position in analysis_results.get("positions_needing_attention", []):
                analysis_text += f"- {position.get('symbol')}: {position.get('reason')}\n"
        
        # Format risk profile
        risk_text = "Risk Profile:\n"
        risk_text += f"- Risk Tolerance: {risk_profile.get('risk_tolerance', 'Unknown')}/10\n"
        risk_text += f"- Max Position Size: {risk_profile.get('max_position_size_percent', 'Unknown')}%\n"
        risk_text += f"- Max Sector Exposure: {risk_profile.get('max_sector_exposure_percent', 'Unknown')}%\n"
        
        # Construct the full prompt
        prompt = f"""
        Based on the portfolio data and analysis, generate specific trade recommendations
        to optimize this portfolio with a risk-averse approach.

        {portfolio_text}
        
        {allocations_text}
        
        {sectors_text}
        
        {analysis_text}
        
        {risk_text}
        
        Please generate specific trade recommendations including:
        
        1. Positions to sell (partial or full) with rationale
        2. Positions to add or increase with rationale
        3. Specific allocation percentages or amounts for each recommendation
        4. Order of priority for these trades
        
        Format each recommendation as:
        - ACTION (BUY/SELL): SYMBOL, AMOUNT or PERCENTAGE, RATIONALE
        
        Focus on addressing overexposures, reducing concentrated risks, and enhancing diversification
        while maintaining a risk-averse approach. Prioritize capital preservation and steady returns
        rather than aggressive growth. Limit any single position to the max position size specified
        in the risk profile.
        """
        
        return prompt