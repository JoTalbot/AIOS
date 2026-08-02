from dataclasses import dataclass


@dataclass
class Identity:
    id: str
    type: str
    owner: str | None = None
