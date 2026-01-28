# config.py
from dataclasses import dataclass, field


@dataclass
class Configurables:
    reference_res: int = field(init=False)
    reference_space: str = field(init=False)


configurables = Configurables()
