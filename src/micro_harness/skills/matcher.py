# src/micro_harness/skills/matcher.py
"""Skill matching with rule-based filtering and LLM precise matching."""

import re
from typing import Any, Optional


class SkillMatcher:
    """Match skills based on user input.

    Uses rule-based filtering (keywords) first, then LLM for precise matching.
    """

    def __init__(self, llm=None, min_confidence: float = 0.7):
        self.llm = llm
        self.min_confidence = min_confidence
        self._cache: dict[str, tuple[str, float]] = {}

    def find_matching_skill(
        self,
        user_input: str,
        skills_with_triggers: list[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Find the best matching skill for user input.

        Args:
            user_input: User's input text
            skills_with_triggers: List of skills with trigger definitions

        Returns:
            Best matching skill dict, or None if no match
        """
        if not skills_with_triggers:
            return None

        # Step 1: Rule-based filtering (keywords match)
        candidates = self._filter_by_keywords(user_input, skills_with_triggers)

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Step 2: LLM precise matching for multiple candidates
        if self.llm:
            best_match = self._llm_match(user_input, candidates)
            if best_match:
                return best_match

        # Fallback: return first candidate
        return candidates[0]

    def _filter_by_keywords(
        self,
        user_input: str,
        skills: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter skills by keyword matching.

        Args:
            user_input: User's input text
            skills: List of skills to filter

        Returns:
            List of skills that match keywords
        """
        candidates = []
        user_input_lower = user_input.lower()

        for skill in skills:
            trigger = skill.get("trigger", {})
            keywords = trigger.get("keywords", [])
            patterns = trigger.get("patterns", [])

            # Check keywords
            keyword_matches = 0
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    keyword_matches += 1

            # Check patterns
            pattern_matches = 0
            for pattern in patterns:
                if re.search(pattern, user_input, re.IGNORECASE):
                    pattern_matches += 1

            # Calculate match score
            if keyword_matches > 0 or pattern_matches > 0:
                score = keyword_matches + pattern_matches * 2
                candidates.append({
                    **skill,
                    "_match_score": score,
                })

        # Sort by match score (highest first)
        candidates.sort(key=lambda x: x.get("_match_score", 0), reverse=True)

        # Remove internal score before returning
        for c in candidates:
            c.pop("_match_score", None)

        return candidates

    def _llm_match(
        self,
        user_input: str,
        candidates: list[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Use LLM to find best match among candidates.

        Args:
            user_input: User's input text
            candidates: List of candidate skills

        Returns:
            Best matching skill, or None
        """
        if not self.llm:
            return None

        # Check cache
        cache_key = user_input[:100]  # Limit cache key length
        if cache_key in self._cache:
            skill_name, confidence = self._cache[cache_key]
            if confidence >= self.min_confidence:
                for skill in candidates:
                    if skill.get("name") == skill_name:
                        return skill
            return None

        # Build prompt
        skill_list = "\n".join([
            f"{i+1}. {s.get('name', 'unknown')}: {s.get('description', '')}"
            for i, s in enumerate(candidates)
        ])

        prompt = f"""Analyze the user input and determine which skill is most relevant.

User input: {user_input}

Available skills:
{skill_list}

Output format:
skill_name|confidence

Where confidence is a number between 0 and 1.
If no skill is relevant, output: NONE|0

Example: code-review|0.85"""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = response.content.strip()

            if content.startswith("NONE"):
                self._cache[cache_key] = ("NONE", 0)
                return None

            if "|" in content:
                parts = content.split("|")
                skill_name = parts[0].strip()
                confidence = float(parts[1].strip())

                # Cache result
                self._cache[cache_key] = (skill_name, confidence)

                # Return skill if confidence is high enough
                if confidence >= self.min_confidence:
                    for skill in candidates:
                        if skill.get("name") == skill_name:
                            return skill

        except Exception:
            pass

        return None

    def clear_cache(self) -> None:
        """Clear the matching cache."""
        self._cache.clear()
