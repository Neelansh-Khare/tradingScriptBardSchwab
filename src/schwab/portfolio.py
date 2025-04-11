"""
Portfolio data structures for the Schwab-AI Portfolio Manager.

This module defines the Portfolio and Position classes
used to represent a portfolio and its positions.
"""

import pandas as pd
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """
    Represents a position in a portfolio.
    """
    symbol: str
    quantity: float
    asset_type: str
    cost_basis: float
    market_value: float
    current_price: float
    instrument_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def unrealized_pl(self) -> float:
        """Calculate unrealized profit/loss."""
        return self.market_value - (self.cost_basis * self.quantity)
    
    @property
    def unrealized_pl_percent(self) -> float:
        """Calculate unrealized profit/loss percentage."""
        if self.cost_basis == 0 or self.quantity == 0:
            return 0
        return (self.current_price / self.cost_basis - 1) * 100
    
    @property
    def weight(self) -> float:
        """
        Calculate the weight of this position in the portfolio.
        This requires the portfolio to set this value.
        """
        return getattr(self, '_weight', 0)
    
    @weight.setter
    def weight(self, value: float):
        """Set the weight of this position."""
        self._weight = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'asset_type': self.asset_type,
            'cost_basis': self.cost_basis,
            'market_value': self.market_value,
            'current_price': self.current_price,
            'unrealized_pl': self.unrealized_pl,
            'unrealized_pl_percent': self.unrealized_pl_percent,
            'weight': self.weight
        }


@dataclass
class Portfolio:
    """
    Represents a portfolio of positions.
    """
    account_id: str
    positions: List[Position]
    account_value: float
    cash_balance: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Calculate additional attributes after initialization."""
        # Calculate position weights
        self._calculate_position_weights()
        
        # Get unique sectors
        self.sectors = self._get_sectors()
        
        # Calculate sector allocations
        self.sector_allocations = self._calculate_sector_allocations()
        
    def _calculate_position_weights(self):
        """Calculate the weight of each position in the portfolio."""
        if self.account_value == 0:
            for position in self.positions:
                position.weight = 0
            return
            
        for position in self.positions:
            position.weight = position.market_value / self.account_value * 100
    
    def _get_sectors(self) -> Set[str]:
        """Get the unique sectors in the portfolio."""
        sectors = set()
        for position in self.positions:
            sector = position.instrument_data.get('fundamental', {}).get('sector', 'Unknown')
            sectors.add(sector)
        return sectors
    
    def _calculate_sector_allocations(self) -> Dict[str, float]:
        """Calculate the allocation percentage for each sector."""
        sector_allocations = {}
        for sector in self.sectors:
            sector_value = sum(p.market_value for p in self.positions 
                              if p.instrument_data.get('fundamental', {}).get('sector', 'Unknown') == sector)
            sector_allocations[sector] = sector_value / self.account_value * 100 if self.account_value > 0 else 0
        return sector_allocations
    
    @property
    def total_market_value(self) -> float:
        """Calculate the total market value of all positions."""
        return sum(position.market_value for position in self.positions)
    
    @property
    def total_cost_basis(self) -> float:
        """Calculate the total cost basis of all positions."""
        return sum(position.cost_basis * position.quantity for position in self.positions)
    
    @property
    def total_unrealized_pl(self) -> float:
        """Calculate the total unrealized profit/loss."""
        return sum(position.unrealized_pl for position in self.positions)
    
    @property
    def total_unrealized_pl_percent(self) -> float:
        """Calculate the total unrealized profit/loss percentage."""
        if self.total_cost_basis == 0:
            return 0
        return self.total_unrealized_pl / self.total_cost_basis * 100
    
    @property
    def cash_allocation(self) -> float:
        """Calculate the percentage of the portfolio allocated to cash."""
        return self.cash_balance / self.account_value * 100 if self.account_value > 0 else 0
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get a position by its symbol."""
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert positions to a pandas DataFrame."""
        positions_data = [position.to_dict() for position in self.positions]
        return pd.DataFrame(positions_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the portfolio to a dictionary for serialization."""
        return {
            'account_id': self.account_id,
            'account_value': self.account_value,
            'cash_balance': self.cash_balance,
            'cash_allocation': self.cash_allocation,
            'total_market_value': self.total_market_value,
            'total_cost_basis': self.total_cost_basis,
            'total_unrealized_pl': self.total_unrealized_pl,
            'total_unrealized_pl_percent': self.total_unrealized_pl_percent,
            'positions': [position.to_dict() for position in self.positions],
            'sector_allocations': self.sector_allocations,
            'timestamp': self.timestamp.isoformat()
        }