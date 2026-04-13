"""PII (Personally Identifiable Information) filtering for claude-hooks."""
from __future__ import annotations

import re
from typing import Any


# Regex patterns for common PII types
_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("SSN", re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b")),
    ("EMAIL", re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")),
    ("PHONE", re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b")),
    ("IP_ADDRESS", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
]


class PIIFilter:
    """Detects and anonymizes PII in text.

    Uses Microsoft Presidio if installed (pip install claude-hooks[pii]),
    falls back to regex-based detection.

    Usage:
        f = PIIFilter()
        anonymized, mapping = f.anonymize("Email john@test.com")
        # anonymized = "Email EMAIL_1"
        # mapping = {"EMAIL_1": "john@test.com"}

        restored = f.deanonymize(anonymized, mapping)
        # restored = "Email john@test.com"
    """

    def __init__(self, *, use_presidio: bool = True):
        self._presidio_analyzer = None
        self._presidio_available = False

        if use_presidio:
            try:
                from presidio_analyzer import AnalyzerEngine
                self._presidio_analyzer = AnalyzerEngine()
                self._presidio_available = True
            except ImportError:
                pass

    def anonymize(self, text: str) -> tuple[str, dict[str, str]]:
        """Replace PII in text with tokens.

        Returns (anonymized_text, mapping) where mapping maps tokens
        back to original values for deanonymization.
        """
        if self._presidio_available:
            return self._anonymize_presidio(text)
        return self._anonymize_regex(text)

    def deanonymize(self, text: str, mapping: dict[str, str]) -> str:
        """Restore original PII values from tokens."""
        result = text
        # Sort by token length descending to avoid partial replacements
        for token, original in sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True):
            result = result.replace(token, original)
        return result

    def _anonymize_regex(self, text: str) -> tuple[str, dict[str, str]]:
        """Regex-based PII detection and anonymization."""
        mapping: dict[str, str] = {}
        counters: dict[str, int] = {}
        result = text

        for pii_type, pattern in _PII_PATTERNS:
            matches = pattern.findall(result)
            for match in matches:
                if match in mapping.values():
                    continue
                counters[pii_type] = counters.get(pii_type, 0) + 1
                token = f"{pii_type}_{counters[pii_type]}"
                mapping[token] = match
                result = result.replace(match, token, 1)

        return result, mapping

    def _anonymize_presidio(self, text: str) -> tuple[str, dict[str, str]]:
        """Presidio-based PII detection and anonymization."""
        results = self._presidio_analyzer.analyze(text=text, language="en")
        mapping: dict[str, str] = {}
        counters: dict[str, int] = {}

        # Sort by start position descending so replacements don't shift indices
        results = sorted(results, key=lambda r: r.start, reverse=True)
        result = text

        for r in results:
            pii_type = r.entity_type
            counters[pii_type] = counters.get(pii_type, 0) + 1
            token = f"{pii_type}_{counters[pii_type]}"
            original = text[r.start : r.end]
            mapping[token] = original
            result = result[:r.start] + token + result[r.end:]

        return result, mapping
