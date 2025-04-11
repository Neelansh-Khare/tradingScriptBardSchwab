"""
Reporting utilities for the Schwab-AI Portfolio Manager.

This module generates reports and visualizations.
"""

import os
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from src.schwab.portfolio import Portfolio

logger = logging.getLogger(__name__)


def generate_report(portfolio: Portfolio, analysis_results: Dict[str, Any], 
                   config: Dict[str, Any]) -> str:
    """
    Generate a detailed report of portfolio analysis.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        analysis_results (Dict[str, Any]): Analysis results.
        config (Dict[str, Any]): Configuration dictionary.
        
    Returns:
        str: Path to the generated report.
    """
    logger.info("Generating portfolio report")
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        'reports'
    )
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create report files
    json_path = os.path.join(reports_dir, f'report_{timestamp}.json')
    html_path = os.path.join(reports_dir, f'report_{timestamp}.html')
    
    # Write JSON report
    write_json_report(portfolio, analysis_results, json_path)
    
    # Generate HTML report
    generate_html_report(portfolio, analysis_results, html_path)
    
    # Generate visualizations
    visualizations_dir = os.path.join(reports_dir, f'visuals_{timestamp}')
    if not os.path.exists(visualizations_dir):
        os.makedirs(visualizations_dir)
        
    generate_visualizations(portfolio, analysis_results, visualizations_dir)
    
    logger.info(f"Report generated at {html_path}")
    return html_path


def write_json_report(portfolio: Portfolio, analysis_results: Dict[str, Any], 
                     json_path: str) -> None:
    """
    Write portfolio and analysis data to a JSON file.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        analysis_results (Dict[str, Any]): Analysis results.
        json_path (str): Path to write the JSON file.
    """
    try:
        # Prepare data
        data = {
            "timestamp": datetime.now().isoformat(),
            "portfolio": portfolio.to_dict(),
            "analysis": analysis_results,
        }
        
        # Write to file
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"JSON report written to {json_path}")
        
    except Exception as e:
        logger.error(f"Failed to write JSON report: {str(e)}")


def generate_html_report(portfolio: Portfolio, analysis_results: Dict[str, Any], 
                        html_path: str) -> None:
    """
    Generate an HTML report of portfolio analysis.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        analysis_results (Dict[str, Any]): Analysis results.
        html_path (str): Path to write the HTML file.
    """
    try:
        # Get portfolio data
        portfolio_data = portfolio.to_dict()
        
        # Get metrics
        metrics = analysis_results.get("metrics", {})
        risk_metrics = analysis_results.get("risk_metrics", {})
        insights = analysis_results.get("insights", {})
        llm_analysis = analysis_results.get("llm_analysis", {})
        
        # Generate HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Portfolio Analysis Report - {datetime.now().strftime('%Y-%m-%d')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333366; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ text-align: left; padding: 8px; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ background-color: #eef6ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .metrics {{ display: flex; flex-wrap: wrap; }}
                .metric {{ width: 200px; margin: 10px; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }}
                .good {{ color: green; }}
                .warning {{ color: orange; }}
                .bad {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>Portfolio Analysis Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Account ID:</strong> {portfolio_data.get('account_id')}</p>
            
            <div class="summary">
                <h2>Portfolio Summary</h2>
                <p><strong>Total Market Value:</strong> ${portfolio_data.get('total_market_value', 0):.2f}</p>
                <p><strong>Cash Balance:</strong> ${portfolio_data.get('cash_balance', 0):.2f} ({portfolio_data.get('cash_allocation', 0):.2f}%)</p>
                <p><strong>Total Unrealized P/L:</strong> ${portfolio_data.get('total_unrealized_pl', 0):.2f} ({portfolio_data.get('total_unrealized_pl_percent', 0):.2f}%)</p>
            </div>
            
            <h2>Portfolio Analysis</h2>
            
            <div class="metrics">
                <div class="metric">
                    <h3>Diversity Score</h3>
                    <p>{metrics.get('diversity_score', 0):.2f}</p>
                </div>
                <div class="metric">
                    <h3>Concentration Score</h3>
                    <p>{metrics.get('concentration_score', 0):.2f}</p>
                </div>
                <div class="metric">
                    <h3>Portfolio Beta</h3>
                    <p>{risk_metrics.get('beta', 'N/A') if risk_metrics.get('beta') is not None else 'N/A'}</p>
                </div>
                <div class="metric">
                    <h3>Sector Concentration</h3>
                    <p>{metrics.get('sector_concentration', 0):.2f}</p>
                </div>
            </div>
            
            <h2>Holdings</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Quantity</th>
                    <th>Current Price</th>
                    <th>Market Value</th>
                    <th>Weight</th>
                    <th>Cost Basis</th>
                    <th>Unrealized P/L</th>
                    <th>P/L %</th>
                </tr>
        """
        
        # Add rows for each position
        for position in portfolio_data.get('positions', []):
            # Determine class for P/L percentage
            pl_class = ''
            pl_percent = position.get('unrealized_pl_percent', 0)
            if pl_percent > 5:
                pl_class = 'good'
            elif pl_percent < -5:
                pl_class = 'bad'
                
            html_content += f"""
                <tr>
                    <td>{position.get('symbol')}</td>
                    <td>{position.get('quantity')}</td>
                    <td>${position.get('current_price', 0):.2f}</td>
                    <td>${position.get('market_value', 0):.2f}</td>
                    <td>{position.get('weight', 0):.2f}%</td>
                    <td>${position.get('cost_basis', 0):.2f}</td>
                    <td>${position.get('unrealized_pl', 0):.2f}</td>
                    <td class="{pl_class}">{position.get('unrealized_pl_percent', 0):.2f}%</td>
                </tr>
            """
            
        html_content += """
            </table>
            
            <h2>Sector Allocation</h2>
            <table>
                <tr>
                    <th>Sector</th>
                    <th>Allocation</th>
                </tr>
        """
        
        # Add rows for each sector
        for sector, allocation in portfolio_data.get('sector_allocations', {}).items():
            html_content += f"""
                <tr>
                    <td>{sector}</td>
                    <td>{allocation:.2f}%</td>
                </tr>
            """
            
        html_content += """
            </table>
            
            <h2>Insights & Recommendations</h2>
        """
        
        # Add insights
        for category, insight in insights.items():
            status = insight.get('status', '')
            message = insight.get('message', '')
            
            status_class = ''
            if status == 'good':
                status_class = 'good'
            elif status == 'warning':
                status_class = 'warning'
            elif status == 'bad' or status == 'high' or status == 'concerning':
                status_class = 'bad'
                
            html_content += f"""
                <div class="insight">
                    <h3>{category.title()}</h3>
                    <p class="{status_class}">{message}</p>
                </div>
            """
            
        # Add LLM analysis
        if llm_analysis.get('raw_text'):
            html_content += """
                <h2>AI Analysis</h2>
                <div class="llm-analysis">
            """
            
            # Format the LLM analysis text with proper HTML paragraphs
            llm_text = llm_analysis.get('raw_text', '')
            paragraphs = llm_text.split('\n\n')
            
            for paragraph in paragraphs:
                if paragraph.strip():
                    html_content += f"<p>{paragraph}</p>\n"
                    
            html_content += """
                </div>
            """
            
        # Close HTML document
        html_content += """
        </body>
        </html>
        """
        
        # Write to file
        with open(html_path, 'w') as f:
            f.write(html_content)
            
        logger.info(f"HTML report written to {html_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate HTML report: {str(e)}")


def generate_visualizations(portfolio: Portfolio, analysis_results: Dict[str, Any], 
                           output_dir: str) -> None:
    """
    Generate visualizations for portfolio analysis.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        analysis_results (Dict[str, Any]): Analysis results.
        output_dir (str): Directory to save visualizations.
    """
    try:
        # Generate pie chart of portfolio weights
        generate_portfolio_pie_chart(portfolio, output_dir)
        
        # Generate sector allocation bar chart
        generate_sector_bar_chart(portfolio, output_dir)
        
        # Generate risk metrics radar chart
        generate_risk_radar_chart(analysis_results.get("risk_metrics", {}), output_dir)
        
        logger.info(f"Visualizations generated in {output_dir}")
        
    except Exception as e:
        logger.error(f"Failed to generate visualizations: {str(e)}")


def generate_portfolio_pie_chart(portfolio: Portfolio, output_dir: str) -> None:
    """
    Generate a pie chart of portfolio weights.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        output_dir (str): Directory to save the chart.
    """
    # Prepare data
    symbols = []
    weights = []
    
    for position in portfolio.positions:
        if position.weight > 1.0:  # Only include positions with significant weight
            symbols.append(position.symbol)
            weights.append(position.weight)
    
    # Add cash
    if portfolio.cash_allocation > 1.0:
        symbols.append("Cash")
        weights.append(portfolio.cash_allocation)
        
    # Create pie chart
    plt.figure(figsize=(10, 8))
    plt.pie(weights, labels=symbols, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    plt.title('Portfolio Allocation by Weight')
    
    # Save chart
    chart_path = os.path.join(output_dir, 'portfolio_weights.png')
    plt.savefig(chart_path)
    plt.close()
    
    logger.info(f"Portfolio weight pie chart saved to {chart_path}")


def generate_sector_bar_chart(portfolio: Portfolio, output_dir: str) -> None:
    """
    Generate a bar chart of sector allocations.
    
    Args:
        portfolio (Portfolio): The portfolio to analyze.
        output_dir (str): Directory to save the chart.
    """
    # Prepare data
    sectors = list(portfolio.sector_allocations.keys())
    allocations = list(portfolio.sector_allocations.values())
    
    # Sort by allocation (descending)
    sorted_indices = np.argsort(allocations)[::-1]
    sectors = [sectors[i] for i in sorted_indices]
    allocations = [allocations[i] for i in sorted_indices]
    
    # Create bar chart
    plt.figure(figsize=(12, 8))
    plt.bar(sectors, allocations)
    plt.xlabel('Sector')
    plt.ylabel('Allocation (%)')
    plt.title('Portfolio Allocation by Sector')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save chart
    chart_path = os.path.join(output_dir, 'sector_allocation.png')
    plt.savefig(chart_path)
    plt.close()
    
    logger.info(f"Sector allocation bar chart saved to {chart_path}")


def generate_risk_radar_chart(risk_metrics: Dict[str, Any], output_dir: str) -> None:
    """
    Generate a radar chart of risk metrics.
    
    Args:
        risk_metrics (Dict[str, Any]): Risk metrics.
        output_dir (str): Directory to save the chart.
    """
    # Check if we have risk metrics
    if not risk_metrics:
        logger.warning("No risk metrics available for radar chart")
        return
        
    # Prepare data
    categories = ['Diversification Risk', 'Market Risk', 'Concentration Risk', 
                 'Sector Risk', 'Overall Risk']
                 
    values = [
        risk_metrics.get('diversification_risk', 0),
        risk_metrics.get('market_risk', 0),
        risk_metrics.get('concentration_risk', 0),
        risk_metrics.get('sector_risk', 0),
        risk_metrics.get('overall_risk_score', 0)
    ]
    
    # Number of variables
    N = len(categories)
    
    # Create angle for each category
    angles = [n / N * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Close the loop
    
    # Add the last value to close the loop
    values += values[:1]
    
    # Create plot
    plt.figure(figsize=(10, 10))
    ax = plt.subplot(111, polar=True)
    
    # Draw the chart
    plt.xticks(angles[:-1], categories, fontsize=12)
    ax.set_rlabel_position(0)
    plt.yticks([20, 40, 60, 80], ["20", "40", "60", "80"], fontsize=10)
    plt.ylim(0, 100)
    
    # Plot data
    ax.plot(angles, values, linewidth=2, linestyle='solid')
    
    # Fill area
    ax.fill(angles, values, alpha=0.4)
    
    # Add title
    plt.title('Portfolio Risk Assessment', size=15, y=1.1)
    
    # Save chart
    chart_path = os.path.join(output_dir, 'risk_radar.png')
    plt.savefig(chart_path)
    plt.close()
    
    logger.info(f"Risk radar chart saved to {chart_path}")