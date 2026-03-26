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
"""Prompt builders for social media simulations.

These produce the same system prompts as the original ``UserInfo.to_system_message()``
method, but packaged as ``BasePromptBuilder`` implementations so they can be
used declaratively via ``SimulationConfig``.
"""
from wonderwall.simulations.base import BasePromptBuilder


def _build_description(user_info) -> str:
    """Extract name + profile description from user_info."""
    name_string = ""
    description_string = ""
    if user_info.name is not None:
        name_string = f"Your name is {user_info.name}."
    if user_info.profile is None:
        return name_string
    if "other_info" not in user_info.profile:
        return name_string
    if "user_profile" in user_info.profile["other_info"]:
        user_profile = user_info.profile["other_info"]["user_profile"]
        if user_profile is not None:
            description_string = f"Your have profile: {user_profile}."
            return f"{name_string}\n{description_string}"
    return name_string


class TwitterPromptBuilder(BasePromptBuilder):
    """Builds the system prompt for a Twitter-style simulation."""

    def build_system_prompt(self, user_info) -> str:
        description = _build_description(user_info)
        return f"""
# OBJECTIVE
You're a Twitter user, and I'll present you with some tweets. After you see the tweets, choose some actions from the following functions.

# SELF-DESCRIPTION
Your actions should be consistent with your self-description and personality.
{description}

# RESPONSE METHOD
Please perform actions by tool calling.
        """


class RedditPromptBuilder(BasePromptBuilder):
    """Builds the system prompt for a Reddit-style simulation."""

    def build_system_prompt(self, user_info) -> str:
        description = _build_description(user_info)
        # Reddit agents have additional demographic info.
        if (user_info.profile is not None
                and "other_info" in user_info.profile):
            other = user_info.profile["other_info"]
            if all(k in other for k in ("gender", "age", "mbti", "country")):
                description += (
                    f"You are a {other['gender']}, "
                    f"{other['age']} years old, with an MBTI "
                    f"personality type of {other['mbti']} from "
                    f"{other['country']}."
                )

        return f"""
# OBJECTIVE
You're a Reddit user, and I'll present you with some posts. After you see the posts, choose some actions from the following functions.

# SELF-DESCRIPTION
Your actions should be consistent with your self-description and personality.
{description}

# RESPONSE METHOD
Please perform actions by tool calling.
"""
