# tests/test_skills_matcher.py
"""Tests for skill matcher module."""

import pytest
from unittest.mock import Mock, MagicMock
from spark.skills.matcher import SkillMatcher


@pytest.fixture
def skills():
    """Sample skills for testing."""
    return [
        {
            "name": "code-review",
            "description": "Review code for issues",
            "trigger": {
                "keywords": ["review", "code"],
                "patterns": [r"review\s+(this\s+)?code"]
            }
        },
        {
            "name": "git-helper",
            "description": "Help with git operations",
            "trigger": {
                "keywords": ["git", "commit", "push", "pull"],
                "patterns": [r"git\s+\w+"]
            }
        },
        {
            "name": "test-runner",
            "description": "Run tests",
            "trigger": {
                "keywords": ["test", "pytest"],
                "patterns": [r"run\s+tests?"]
            }
        }
    ]


class TestSkillMatcher:
    """Skill matcher tests."""

    def test_init(self):
        """Test initialization."""
        matcher = SkillMatcher()
        assert matcher.llm is None
        assert matcher.min_confidence == 0.7
        assert matcher._cache == {}

    def test_init_with_llm(self):
        """Test initialization with LLM."""
        mock_llm = Mock()
        matcher = SkillMatcher(llm=mock_llm, min_confidence=0.8)
        assert matcher.llm == mock_llm
        assert matcher.min_confidence == 0.8

    def test_find_matching_skill_empty_skills(self):
        """Test with empty skills list."""
        matcher = SkillMatcher()
        result = matcher.find_matching_skill("review this code", [])
        assert result is None

    def test_find_matching_skill_keyword_match(self, skills):
        """Test keyword matching."""
        matcher = SkillMatcher()
        result = matcher.find_matching_skill("please review this code", skills)

        assert result is not None
        assert result["name"] == "code-review"

    def test_find_matching_skill_pattern_match(self, skills):
        """Test pattern matching."""
        matcher = SkillMatcher()
        result = matcher.find_matching_skill("git status", skills)

        assert result is not None
        assert result["name"] == "git-helper"

    def test_find_matching_skill_no_match(self, skills):
        """Test no match case."""
        matcher = SkillMatcher()
        result = matcher.find_matching_skill("what is the weather today", skills)

        assert result is None

    def test_filter_by_keywords(self, skills):
        """Test keyword filtering."""
        matcher = SkillMatcher()
        candidates = matcher._filter_by_keywords("run pytest for me", skills)

        assert len(candidates) >= 1
        assert any(s["name"] == "test-runner" for s in candidates)

    def test_filter_by_keywords_multiple_matches(self, skills):
        """Test multiple keyword matches."""
        matcher = SkillMatcher()
        candidates = matcher._filter_by_keywords("review code and run git status", skills)

        # Should match code-review and git-helper
        assert len(candidates) >= 2

    def test_filter_by_patterns(self, skills):
        """Test pattern filtering."""
        matcher = SkillMatcher()
        candidates = matcher._filter_by_keywords("run tests please", skills)

        assert len(candidates) >= 1
        assert any(s["name"] == "test-runner" for s in candidates)

    def test_llm_match_no_llm(self, skills):
        """Test LLM match without LLM."""
        matcher = SkillMatcher()
        result = matcher._llm_match("review code", skills)

        assert result is None

    def test_llm_match_with_llm(self, skills):
        """Test LLM match with LLM."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "code-review|0.9"
        mock_llm.chat.return_value = mock_response

        matcher = SkillMatcher(llm=mock_llm, min_confidence=0.7)
        result = matcher._llm_match("review this code", skills[:2])

        assert result is not None
        assert result["name"] == "code-review"

    def test_llm_match_low_confidence(self, skills):
        """Test LLM match with low confidence."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "code-review|0.3"
        mock_llm.chat.return_value = mock_response

        matcher = SkillMatcher(llm=mock_llm, min_confidence=0.7)
        result = matcher._llm_match("review this code", skills[:2])

        assert result is None

    def test_llm_match_none_response(self, skills):
        """Test LLM match with NONE response."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "NONE|0"
        mock_llm.chat.return_value = mock_response

        matcher = SkillMatcher(llm=mock_llm)
        result = matcher._llm_match("random input", skills[:2])

        assert result is None

    def test_llm_match_caching(self, skills):
        """Test LLM match caching."""
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "code-review|0.9"
        mock_llm.chat.return_value = mock_response

        matcher = SkillMatcher(llm=mock_llm)

        # First call
        matcher._llm_match("review code", skills[:2])
        # Second call with same input (should use cache)
        matcher._llm_match("review code", skills[:2])

        # LLM should only be called once due to caching
        mock_llm.chat.assert_called_once()

    def test_llm_match_exception(self, skills):
        """Test LLM match handles exceptions."""
        mock_llm = Mock()
        mock_llm.chat.side_effect = Exception("LLM error")

        matcher = SkillMatcher(llm=mock_llm)
        result = matcher._llm_match("review code", skills[:2])

        assert result is None

    def test_clear_cache(self):
        """Test cache clearing."""
        matcher = SkillMatcher()
        matcher._cache["test"] = ("skill", 0.9)

        matcher.clear_cache()

        assert matcher._cache == {}

    def test_find_matching_skill_single_candidate(self):
        """Test with single candidate returns directly."""
        skills = [{
            "name": "only-skill",
            "trigger": {"keywords": ["only"], "patterns": []}
        }]

        matcher = SkillMatcher()
        result = matcher.find_matching_skill("only one", skills)

        assert result is not None
        assert result["name"] == "only-skill"

    def test_find_matching_skill_fallback(self):
        """Test fallback to first candidate when no LLM."""
        skills = [
            {"name": "skill-a", "trigger": {"keywords": ["test"], "patterns": []}},
            {"name": "skill-b", "trigger": {"keywords": ["test"], "patterns": []}}
        ]

        matcher = SkillMatcher()
        result = matcher.find_matching_skill("test something", skills)

        # Should return first candidate when multiple match and no LLM
        assert result is not None