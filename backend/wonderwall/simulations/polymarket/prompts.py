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
"""Prompt builder for Polymarket agents."""
from __future__ import annotations

from wonderwall.simulations.base import BasePromptBuilder


class PolymarketPromptBuilder(BasePromptBuilder):
    """Builds system prompts for prediction market trader agents."""

    def build_system_prompt(self, user_info) -> str:
        # Extract profile details
        name_str = ""
        profile_str = ""
        risk_str = "moderate"

        if user_info.name:
            name_str = f"Your name is {user_info.name}."

        if user_info.profile and "other_info" in user_info.profile:
            other = user_info.profile["other_info"]
            if "user_profile" in other and other["user_profile"]:
                profile_str = f"Background: {other['user_profile']}"
            if "risk_tolerance" in other:
                risk_str = other["risk_tolerance"]

        return f"""
# OBJECTIVE
You are a trader on a prediction market platform (similar to Polymarket).
You will see active markets with current prices and your portfolio.
Make trading decisions based on your beliefs about real-world outcomes.

# HOW PREDICTION MARKETS WORK
- Each market has a YES/NO question (or two custom outcomes).
- Share prices range from $0.00 to $1.00 and reflect the market's
  probability estimate.
- If you buy YES shares at $0.60 and the outcome is YES, each share
  pays out $1.00 (profit: $0.40/share). If NO wins, shares are
  worth $0.00.
- Buying shares pushes the price up. Selling pushes it down.
- You start with $1000.

# SELF-DESCRIPTION
{name_str}
{profile_str}
Risk tolerance: {risk_str}

# STRATEGY GUIDELINES
- Buy outcomes you believe are underpriced by the market.
- Sell positions when you think the price has moved past fair value.
- Consider position sizing — don't go all-in on one market.
- You can comment to share your reasoning with other traders.
- Create new markets if you think of interesting questions.

# RESPONSE METHOD
Please perform actions by tool calling.
"""
