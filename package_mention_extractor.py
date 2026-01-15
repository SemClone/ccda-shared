"""
Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>
All Rights Reserved.

This file is part of CCDA, a proprietary commercial software project.
Unauthorized copying, distribution, or use is strictly prohibited.
"""
import re
from typing import List, Dict, Optional


class PackageMentionExtractor:
    """
    Extract package mentions from text content using multiple detection strategies.
    
    Supports three detection methods:
    1. PURL exact match (confidence: 1.0)
    2. GitHub URL match (confidence: 0.9)
    3. Package name match with ecosystem context (confidence: 0.6-0.8)
    
    Only returns mentions with confidence >= 0.7 (configurable threshold).
    """
    
    # Regex patterns for detection
    PURL_PATTERN = re.compile(
        r'pkg:([a-z0-9-]+)/([a-zA-Z0-9._/-]+)(?:@([^\s]+))?',
        re.IGNORECASE
    )
    
    GITHUB_PATTERN = re.compile(
        r'github\.com/([a-zA-Z0-9-]+)/([a-zA-Z0-9._-]+)',
        re.IGNORECASE
    )
    
    # Ecosystem keywords for confidence boosting
    ECOSYSTEM_KEYWORDS = {
        'npm': ['npm', 'node', 'javascript', 'yarn', 'pnpm', 'package.json'],
        'pypi': ['pip', 'python', 'pypi', 'requirements.txt'],
        'maven': ['maven', 'java', 'gradle', 'pom.xml'],
        'golang': ['go get', 'golang', 'go module', 'go.mod'],
        'go': ['go get', 'golang', 'go module', 'go.mod'],
        'cargo': ['cargo', 'rust', 'crates.io', 'cargo.toml'],
        'nuget': ['nuget', '.net', 'dotnet', 'csharp'],
        'packagist': ['composer', 'php', 'packagist'],
        'rubygems': ['gem', 'ruby', 'bundler', 'gemfile'],
        'hex': ['hex', 'elixir', 'erlang', 'mix.exs'],
    }
    
    def __init__(self, min_confidence: float = 0.7):
        """
        Initialize the extractor.
        
        Args:
            min_confidence: Minimum confidence threshold (0.0-1.0). Default: 0.7
        """
        self.min_confidence = min_confidence
    
    def extract_mentions(
        self,
        content: str,
        tracked_packages: List[Dict]
    ) -> List[Dict]:
        """
        Extract package mentions from content.
        
        Args:
            content: Text content to search (title + body)
            tracked_packages: List of tracked packages with fields:
                - id: Package ID
                - name: Package name
                - purl: Package URL
                - ecosystem: Package ecosystem
                - github_url: GitHub repository URL (optional)
                - repo_url: Repository URL (optional)
        
        Returns:
            List of mentions with structure:
            {
                'package_id': int,
                'mention_type': str,  # 'purl', 'github_url', 'package_name'
                'mention_text': str,
                'confidence': float,
                'context_snippet': str
            }
        """
        if not content or not tracked_packages:
            return []
        
        mentions = []
        content_lower = content.lower()
        
        # Strategy 1: PURL exact match (highest confidence)
        mentions.extend(self._extract_purl_mentions(content, tracked_packages))
        
        # Strategy 2: GitHub URL match (high confidence)
        mentions.extend(self._extract_github_mentions(content, tracked_packages))
        
        # Strategy 3: Package name match (variable confidence)
        mentions.extend(self._extract_name_mentions(content, content_lower, tracked_packages))
        
        # Deduplicate and filter by confidence
        mentions = self._deduplicate_mentions(mentions)
        mentions = [m for m in mentions if m['confidence'] >= self.min_confidence]
        
        return mentions
    
    def _extract_purl_mentions(self, content: str, tracked_packages: List[Dict]) -> List[Dict]:
        """Extract mentions via PURL pattern matching."""
        mentions = []
        
        for match in self.PURL_PATTERN.finditer(content):
            ecosystem, name_part, version = match.groups()
            purl_base = f"pkg:{ecosystem}/{name_part}"
            
            # Find matching package
            for pkg in tracked_packages:
                if pkg['purl'].startswith(purl_base):
                    mentions.append({
                        'package_id': pkg['id'],
                        'mention_type': 'purl',
                        'mention_text': match.group(0),
                        'confidence': 1.0,
                        'context_snippet': self._extract_context(
                            content, match.start(), match.end()
                        )
                    })
                    break
        
        return mentions
    
    def _extract_github_mentions(self, content: str, tracked_packages: List[Dict]) -> List[Dict]:
        """Extract mentions via GitHub URL matching."""
        mentions = []
        
        for match in self.GITHUB_PATTERN.finditer(content):
            owner, repo = match.groups()
            github_url = f"https://github.com/{owner}/{repo}"
            github_url_lower = github_url.lower()
            
            # Match against github_url or repo_url fields
            for pkg in tracked_packages:
                pkg_github = (pkg.get('github_url') or '').lower()
                pkg_repo = (pkg.get('repo_url') or '').lower()
                
                if pkg_github == github_url_lower or pkg_repo == github_url_lower:
                    mentions.append({
                        'package_id': pkg['id'],
                        'mention_type': 'github_url',
                        'mention_text': match.group(0),
                        'confidence': 0.9,
                        'context_snippet': self._extract_context(
                            content, match.start(), match.end()
                        )
                    })
                    break
        
        return mentions
    
    def _extract_name_mentions(
        self,
        content: str,
        content_lower: str,
        tracked_packages: List[Dict]
    ) -> List[Dict]:
        """Extract mentions via package name matching with ecosystem context."""
        mentions = []
        
        for pkg in tracked_packages:
            pkg_name = pkg['name']
            ecosystem = pkg.get('ecosystem', '').lower()
            
            # Word boundary match (case-insensitive)
            pattern = re.compile(r'\b' + re.escape(pkg_name) + r'\b', re.IGNORECASE)
            
            for match in pattern.finditer(content):
                start, end = match.start(), match.end()
                context = self._extract_context(content, start, end, window=100)
                context_lower = context.lower()
                
                # Calculate confidence based on ecosystem keywords
                base_confidence = 0.6
                ecosystem_boost = self._calculate_ecosystem_boost(context_lower, ecosystem)
                final_confidence = min(base_confidence + ecosystem_boost, 1.0)
                
                mentions.append({
                    'package_id': pkg['id'],
                    'mention_type': 'package_name',
                    'mention_text': match.group(0),
                    'confidence': final_confidence,
                    'context_snippet': context
                })
        
        return mentions
    
    def _extract_context(
        self,
        text: str,
        start: int,
        end: int,
        window: int = 50
    ) -> str:
        """
        Extract surrounding context from text.
        
        Args:
            text: Full text
            start: Match start position
            end: Match end position
            window: Characters before/after (default: 50)
        
        Returns:
            Context snippet with ellipsis if truncated
        """
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        snippet = text[context_start:context_end].strip()
        
        # Add ellipsis if truncated
        if context_start > 0:
            snippet = '...' + snippet
        if context_end < len(text):
            snippet = snippet + '...'
        
        return snippet
    
    def _calculate_ecosystem_boost(self, context: str, ecosystem: str) -> float:
        """
        Calculate confidence boost based on ecosystem keywords in context.
        
        Args:
            context: Context text (lowercased)
            ecosystem: Package ecosystem
        
        Returns:
            Boost value (0.0 or 0.2)
        """
        keywords = self.ECOSYSTEM_KEYWORDS.get(ecosystem, [])
        
        for keyword in keywords:
            if keyword.lower() in context:
                return 0.2  # Boost confidence by 20%
        
        return 0.0
    
    def _deduplicate_mentions(self, mentions: List[Dict]) -> List[Dict]:
        """
        Deduplicate mentions by keeping highest confidence per package.
        
        If a package is mentioned multiple ways (PURL + name), keep the
        highest confidence match.
        
        Args:
            mentions: List of all mentions
        
        Returns:
            Deduplicated list (one mention per package)
        """
        seen = {}
        
        for mention in mentions:
            pkg_id = mention['package_id']
            
            if pkg_id not in seen or mention['confidence'] > seen[pkg_id]['confidence']:
                seen[pkg_id] = mention
        
        return list(seen.values())
