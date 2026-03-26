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
"""Polymarket agent environment — what the agent sees each turn."""
from __future__ import annotations

import json

from wonderwall.simulations.base import BaseEnvironment


class PolymarketEnvironment(BaseEnvironment):
    """Converts Polymarket state into the text prompt the agent observes."""

    async def to_text_prompt(self) -> str:
        # Fetch current portfolio
        portfolio = await self.action.view_portfolio()
        # Fetch active markets
        markets = await self.action.browse_markets()

        parts = []

        if portfolio.get("success"):
            parts.append(
                f"YOUR PORTFOLIO:\n"
                f"  Cash balance: ${portfolio['balance']:.2f}"
            )
            if portfolio.get("positions"):
                parts.append("  Your positions:")
                for pos in portfolio["positions"]:
                    parts.append(
                        f"    - Market #{pos['market_id']}: "
                        f"\"{pos['question']}\" — "
                        f"{pos['shares']:.1f} {pos['outcome']} shares "
                        f"@ ${pos['current_price']:.3f} "
                        f"(value: ${pos['current_value']:.2f})"
                    )
            else:
                parts.append("  You have no open positions.")

        if markets.get("success") and markets.get("markets"):
            parts.append("\nACTIVE MARKETS:")
            for m in markets["markets"]:
                # Extract price keys dynamically
                price_keys = [k for k in m if k.startswith("price_")]
                price_str = ", ".join(
                    f"{k.replace('price_', '')}: "
                    f"${m[k]:.3f}"
                    for k in price_keys
                )
                parts.append(
                    f"  #{m['market_id']}: \"{m['question']}\" "
                    f"[{price_str}] "
                    f"({m['num_trades']} trades)"
                )
        else:
            parts.append("\nNo active markets yet.")

        parts.append(
            "\nChoose an action based on your beliefs, risk tolerance, "
            "and portfolio. You can buy/sell shares, create markets, "
            "comment, or do nothing."
        )

        return "\n".join(parts)
