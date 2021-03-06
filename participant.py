from dataclasses import dataclass


@dataclass
class Participant:
    id: int
    name: str
    exited: bool = False
