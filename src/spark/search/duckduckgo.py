# src/spark/search/duckduckgo.py
"""DuckDuckGo search integration using their instant answer API.

No API key required - free and privacy-focused.
"""

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# DuckDuckGo Instant Answer API endpoint
DDG_API = "https://api.duckduckgo.com/"
# User agent for requests
USER_AGENT = "Spark/1.0"


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str = "duckduckgo"


@dataclass
class SearchResponse:
    """Search response with multiple results."""
    query: str
    results: List[SearchResult]
    abstract: Optional[str] = None  # Direct answer if available
    source: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_text(self, max_results: int = 5) -> str:
        """Format results as text for LLM context.

        Args:
            max_results: Maximum results to include

        Returns:
            str: Formatted text
        """
        lines = [f"Search: {self.query}"]

        if self.abstract:
            lines.append(f"\nAnswer: {self.abstract}")
            if self.source:
                lines.append(f"Source: {self.source}")

        if self.results:
            lines.append(f"\nResults ({len(self.results)}):")
            for i, r in enumerate(self.results[:max_results], 1):
                lines.append(f"\n{i}. {r.title}")
                lines.append(f"   {r.snippet[:200]}")
                lines.append(f"   URL: {r.url}")

        return "\n".join(lines)


class DuckDuckGoSearch:
    """DuckDuckGo search client.

    Uses DuckDuckGo's instant answer API - no API key required.
    Privacy-focused and free to use.
    """

    def __init__(self, timeout: int = 10):
        """Initialize search client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    def search(self, query: str, max_results: int = 5) -> SearchResponse:
        """Search DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            SearchResponse: Search results
        """
        # Build API URL
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        url = f"{DDG_API}?{urllib.parse.urlencode(params)}"

        try:
            # Make request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT}
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Parse response
            return self._parse_response(query, data, max_results)

        except urllib.error.URLError as e:
            logger.warning(f"Search failed: {e}")
            return SearchResponse(
                query=query,
                results=[],
                abstract=f"Search error: {e}",
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse search response: {e}")
            return SearchResponse(
                query=query,
                results=[],
            )
        except Exception as e:
            logger.warning(f"Unexpected search error: {e}")
            return SearchResponse(
                query=query,
                results=[],
            )

    def _parse_response(self, query: str, data: dict,
                        max_results: int) -> SearchResponse:
        """Parse DuckDuckGo API response.

        Args:
            query: Original query
            data: API response data
            max_results: Max results to include

        Returns:
            SearchResponse: Parsed results
        """
        results = []
        abstract = None
        source = None

        # Get abstract (direct answer)
        if data.get("Abstract"):
            abstract = data["Abstract"]
            source = data.get("AbstractSource", "")

        # Get abstract URL if available
        abstract_url = data.get("AbstractURL", "")

        # Get related topics
        related = data.get("RelatedTopics", [])
        for topic in related[:max_results]:
            # Some topics have nested results
            if "Topics" in topic:
                for subtopic in topic["Topics"][:max_results - len(results)]:
                    result = self._parse_topic(subtopic)
                    if result:
                        results.append(result)
            else:
                result = self._parse_topic(topic)
                if result:
                    results.append(result)

            if len(results) >= max_results:
                break

        # Get results from "Results" field
        for item in data.get("Results", []):
            if len(results) >= max_results:
                break
            if item.get("FirstURL") and item.get("Text"):
                results.append(SearchResult(
                    title=item.get("Text", "").split(" - ")[0],
                    url=item["FirstURL"],
                    snippet=item.get("Text", ""),
                ))

        return SearchResponse(
            query=query,
            results=results,
            abstract=abstract,
            source=source,
        )

    def _parse_topic(self, topic: dict) -> Optional[SearchResult]:
        """Parse a related topic.

        Args:
            topic: Topic data

        Returns:
            Optional[SearchResult]: Parsed result or None
        """
        url = topic.get("FirstURL", "")
        text = topic.get("Text", "")

        if not url or not text:
            return None

        # Extract title from text
        title = text.split(" - ")[0] if " - " in text else text[:100]

        return SearchResult(
            title=title,
            url=url,
            snippet=text,
        )

    def quick_search(self, query: str) -> str:
        """Quick search returning text for LLM context.

        Args:
            query: Search query

        Returns:
            str: Formatted search results
        """
        response = self.search(query)
        return response.to_text()

    def get_definition(self, term: str) -> Optional[str]:
        """Get definition of a term.

        Args:
            term: Term to define

        Returns:
            Optional[str]: Definition or None
        """
        response = self.search(f"define {term}")
        if response.abstract:
            return response.abstract
        return None

    def get_answer(self, question: str) -> Optional[str]:
        """Get direct answer to a question.

        Args:
            question: Question to answer

        Returns:
            Optional[str]: Answer or None
        """
        response = self.search(question)
        if response.abstract:
            return f"{response.abstract}\nSource: {response.source}"
        if response.results:
            r = response.results[0]
            return f"{r.snippet}\nSource: {r.url}"
        return None
