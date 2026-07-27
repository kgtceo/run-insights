"""Offline test doubles — no API key, no network."""

from __future__ import annotations

import pytest

from run_insights.config import Settings


class FakeClient:
    """Returns a scripted feedback string so the Coach's grounding pass runs offline.

    `structured` ignores the schema and returns an object exposing `.feedback`, mimicking the
    analyzer's internal `_Feedback` model.
    """

    def __init__(self, feedback: str) -> None:
        self._feedback = feedback
        self.calls = 0

    def structured(self, *, schema, system, user, model=None):
        self.calls += 1
        return schema(feedback=self._feedback)


@pytest.fixture
def settings() -> Settings:
    return Settings(anthropic_api_key="test-key")
