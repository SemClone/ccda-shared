"""
Content Extraction Utility for Media Monitoring

Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.

This file is part of CCDA, a proprietary commercial software project.
Unauthorized copying, distribution, or use is strictly prohibited.
"""

import re
import asyncio
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
import html2text
from readability import Document


class ContentExtractor:
    """
    Extract clean text content from HTML and URLs.

    Features:
    - HTML to plain text conversion
    - External URL detection and fetching
    - Word count calculation
    - Content quality filtering
    - Timeout and error handling
    """

    def __init__(
        self,
        min_word_count: int = 50,
        timeout_seconds: int = 10,
        user_agent: str = "CCDA-MediaMonitor/1.0 (+https://ccda.semcl.one)"
    ):
        """
        Initialize content extractor.

        Args:
            min_word_count: Minimum word count for valid content
            timeout_seconds: HTTP request timeout
            user_agent: User agent string for HTTP requests
        """
        self.min_word_count = min_word_count
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

        # Initialize html2text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # Don't wrap lines

    def extract_from_html(
        self,
        html_content: str,
        base_url: Optional[str] = None
    ) -> Dict:
        """
        Extract text and metadata from HTML content.

        Args:
            html_content: Raw HTML string
            base_url: Base URL for resolving relative links

        Returns:
            Dictionary with:
                - text: Plain text content
                - word_count: Number of words
                - external_urls: List of external URLs found
                - title: Extracted title (if available)
                - quality_ok: Boolean indicating if content meets minimum quality
        """
        try:
            # Use readability to extract main content
            doc = Document(html_content)
            article_html = doc.summary()
            article_title = doc.short_title()

            # Convert HTML to plain text
            text = self.html_converter.handle(article_html)

            # Clean up text
            text = self._clean_text(text)

            # Calculate word count
            word_count = len(text.split())

            # Extract URLs
            external_urls = self._extract_urls(html_content, base_url)

            return {
                "text": text,
                "word_count": word_count,
                "external_urls": external_urls,
                "title": article_title,
                "quality_ok": word_count >= self.min_word_count
            }

        except Exception as e:
            return {
                "text": "",
                "word_count": 0,
                "external_urls": [],
                "title": None,
                "quality_ok": False,
                "error": str(e)
            }

    async def fetch_and_extract(
        self,
        url: str,
        follow_redirects: bool = True
    ) -> Dict:
        """
        Fetch URL and extract content.

        Args:
            url: URL to fetch
            follow_redirects: Whether to follow HTTP redirects

        Returns:
            Dictionary with extracted content (same as extract_from_html)
            plus 'url' and 'status_code' fields
        """
        result = {
            "url": url,
            "status_code": None,
            "text": "",
            "word_count": 0,
            "external_urls": [],
            "title": None,
            "quality_ok": False
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=follow_redirects,
                headers={"User-Agent": self.user_agent}
            ) as client:
                response = await client.get(url)
                result["status_code"] = response.status_code

                if response.status_code == 200:
                    html_content = response.text
                    extraction = self.extract_from_html(html_content, base_url=url)
                    result.update(extraction)
                else:
                    result["error"] = f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            result["error"] = "Timeout"
        except httpx.RequestError as e:
            result["error"] = f"Request error: {str(e)}"
        except Exception as e:
            result["error"] = f"Extraction error: {str(e)}"

        return result

    async def fetch_multiple_urls(
        self,
        urls: List[str],
        max_concurrent: int = 3
    ) -> List[Dict]:
        """
        Fetch and extract content from multiple URLs concurrently.

        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum concurrent requests

        Returns:
            List of extraction results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url: str) -> Dict:
            async with semaphore:
                return await self.fetch_and_extract(url)

        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "url": urls[i],
                    "error": str(result),
                    "text": "",
                    "word_count": 0,
                    "external_urls": [],
                    "quality_ok": False
                })
            else:
                processed_results.append(result)

        return processed_results

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.

        - Remove excessive whitespace
        - Remove navigation/footer artifacts
        - Normalize newlines
        """
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove excessive spaces
        text = re.sub(r' {2,}', ' ', text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # Remove empty lines at start/end
        text = text.strip()

        return text

    def _extract_urls(
        self,
        html_content: str,
        base_url: Optional[str] = None
    ) -> List[str]:
        """
        Extract unique external URLs from HTML.

        Args:
            html_content: Raw HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of unique absolute URLs
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            urls = set()

            # Extract from <a> tags
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Resolve relative URLs
                if base_url:
                    href = urljoin(base_url, href)

                # Parse URL
                parsed = urlparse(href)

                # Only include http/https URLs
                if parsed.scheme in ['http', 'https']:
                    # Exclude fragments
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if parsed.query:
                        clean_url += f"?{parsed.query}"

                    urls.add(clean_url)

            return sorted(list(urls))

        except Exception:
            return []

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text.

        Args:
            text: Plain text string

        Returns:
            Word count
        """
        return len(text.split())

    @staticmethod
    def truncate_text(text: str, max_chars: int = 5000) -> str:
        """
        Truncate text to maximum character count.

        Args:
            text: Text to truncate
            max_chars: Maximum characters

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_chars:
            return text

        return text[:max_chars - 3] + "..."


# Example usage
if __name__ == "__main__":
    async def test():
        extractor = ContentExtractor(min_word_count=50)

        # Test with a URL
        result = await extractor.fetch_and_extract(
            "https://krebsonsecurity.com/feed/"
        )

        print(f"Title: {result['title']}")
        print(f"Word count: {result['word_count']}")
        print(f"Quality OK: {result['quality_ok']}")
        print(f"External URLs: {len(result['external_urls'])}")
        print(f"\nFirst 500 chars:\n{result['text'][:500]}")

    asyncio.run(test())
