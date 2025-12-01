# config.py
from dataclasses import dataclass, field, fields

@dataclass
class Configurables:
    reference_res: int = field(init=False)

configurables = Configurables()
