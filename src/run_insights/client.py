"""Anthropic structured-output helper (forced tool use + validation retry)."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ValidationError

from .config import Settings

if TYPE_CHECKING:
    from anthropic import Anthropic

T = TypeVar("T", bound=BaseModel)


class StructuredCallError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: Settings, anthropic: "Anthropic | None" = None) -> None:
        self._settings = settings
        if anthropic is None:
            from anthropic import Anthropic

            anthropic = Anthropic(api_key=settings.anthropic_api_key)
        self._client = anthropic

    def structured(self, *, schema: type[T], system: str, user: str, model: str | None = None) -> T:
        tool_name = f"emit_{schema.__name__.lower()}"
        tool = {
            "name": tool_name,
            "description": f"Return the result as a {schema.__name__}.",
            "input_schema": schema.model_json_schema(),
        }
        messages: list[dict] = [{"role": "user", "content": user}]
        last: Exception | None = None
        for _ in range(self._settings.max_schema_retries + 1):
            resp = self._client.messages.create(
                model=model or self._settings.model,
                max_tokens=self._settings.max_tokens,
                system=system,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
                messages=messages,
            )
            block = next(
                (b for b in resp.content if getattr(b, "type", None) == "tool_use" and b.name == tool_name),
                None,
            )
            if block is None:
                last = StructuredCallError("model did not call the output tool")
                continue
            try:
                return schema.model_validate(block.input)
            except ValidationError as exc:
                last = exc
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({"role": "user", "content": f"Failed validation:\n{exc}\nRetry with valid input."})
        raise StructuredCallError(f"No schema-valid {schema.__name__}: {last}")
