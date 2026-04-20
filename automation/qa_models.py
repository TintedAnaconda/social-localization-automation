from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Issue:
    row_number: Optional[int]
    column: str
    severity: str
    rule: str
    message: str
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)