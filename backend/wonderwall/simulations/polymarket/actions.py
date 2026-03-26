# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
"""Polymarket agent actions — the tools the LLM can call."""
from __future__ import annotations

from wonderwall.simulations.base import BaseAction


class PolymarketAction(BaseAction):
    """Actions available to agents in a prediction market simulation."""

    async def browse_markets(self):
        """Browse active prediction markets with current prices.

        Returns:
            dict: A dictionary with 'success' and 'markets' containing a
                list of active markets with prices and trade volume.

            Example:
            {
                "success": True,
                "markets": [
                    {
                        "market_id": 1,
                        "question": "Will BTC exceed $100k by end of 2025?",
                        "price_YES": 0.65,
                        "price_NO": 0.35,
                        "num_trades": 12,
                        "created_at": "2024-01-01T00:00:00"
                    }
                ]
            }
        """
        return await self.perform_action(None, "browse_markets")

    async def buy_shares(self, market_id: int, outcome: str,
                         amount_usd: float):
        """Buy shares of an outcome in a prediction market.

        Spend USD to buy shares. The price is determined by the AMM — buying
        more shares pushes the price up.

        Args:
            market_id (int): The ID of the market to trade in.
            outcome (str): The outcome to buy (e.g. 'YES' or 'NO').
            amount_usd (float): How many USD to spend.

        Returns:
            dict: Contains 'shares_received', 'effective_price', 'total_cost'.

            Example:
            {
                "success": True,
                "shares_received": 15.5,
                "effective_price": 0.645,
                "total_cost": 10.0
            }
        """
        return await self.perform_action(
            (market_id, outcome, amount_usd), "buy_shares"
        )

    async def sell_shares(self, market_id: int, outcome: str,
                          num_shares: float):
        """Sell shares of an outcome back to the market.

        Sell shares to receive USD. Selling pushes the price down.

        Args:
            market_id (int): The ID of the market.
            outcome (str): The outcome whose shares to sell.
            num_shares (float): Number of shares to sell.

        Returns:
            dict: Contains 'usd_received' and 'effective_price'.
        """
        return await self.perform_action(
            (market_id, outcome, num_shares), "sell_shares"
        )

    async def view_portfolio(self):
        """View your current cash balance and market positions.

        Returns:
            dict: Contains 'balance' (USD) and 'positions' (list of holdings).

            Example:
            {
                "success": True,
                "balance": 850.0,
                "positions": [
                    {
                        "market_id": 1,
                        "question": "Will BTC exceed $100k?",
                        "outcome": "YES",
                        "shares": 15.5,
                        "current_price": 0.65,
                        "current_value": 10.08
                    }
                ]
            }
        """
        return await self.perform_action(None, "view_portfolio")

    async def create_market(self, question: str,
                            outcome_a: str = "YES",
                            outcome_b: str = "NO"):
        """Create a new prediction market.

        Args:
            question (str): The question the market is about.
            outcome_a (str): First outcome label (default: 'YES').
            outcome_b (str): Second outcome label (default: 'NO').

        Returns:
            dict: Contains 'market_id' of the newly created market.
        """
        return await self.perform_action(
            (question, outcome_a, outcome_b), "create_market"
        )

    async def comment_on_market(self, market_id: int, content: str):
        """Post a comment on a prediction market.

        Args:
            market_id (int): The market to comment on.
            content (str): Your comment text.
        """
        return await self.perform_action(
            (market_id, content), "comment_on_market"
        )
