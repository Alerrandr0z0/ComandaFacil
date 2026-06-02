from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    name: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Nome da categoria não pode ser vazio.")

    def __str__(self) -> str:
        return self.name
