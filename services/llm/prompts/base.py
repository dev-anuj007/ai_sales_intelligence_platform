from __future__ import annotations

from typing import Any


class PromptTemplate:
    """Base class for versioned prompt templates with parameter substitution."""

    version: str
    use_case: str
    template: str

    def render(self, **kwargs: Any) -> str:
        """Render template with provided variables.

        Args:
            **kwargs: Variables to substitute in template using {variable} syntax

        Returns:
            Rendered prompt string with substitutions applied

        Raises:
            KeyError: If required template variable is missing from kwargs
        """
        return self.template.format(**kwargs)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"version={self.version}, use_case={self.use_case})"
        )
