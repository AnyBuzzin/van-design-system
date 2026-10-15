"""Legacy shelf API backed by the canonical V5 cabinet expressions."""

from dataclasses import dataclass
from functools import lru_cache


@lru_cache(maxsize=1)
def _reference_assembly():
    # Lazy imports keep the legacy facade independent of module import order.
    from ..modules.cabinet import build_cabinet
    from ..schemas.cabinet_spec import CabinetSpec
    return build_cabinet(CabinetSpec())


@dataclass(frozen=True)
class DadoShelf:
    cabinet_width_mm: float
    plywood_mm: float
    dado_depth_mm: float
    end_clearance_mm: float

    def __post_init__(self) -> None:
        """Reject invalid geometry before any derived dimension can be read."""
        self.validate()

    def validate(self) -> None:
        if self.cabinet_width_mm <= 2 * self.plywood_mm:
            raise ValueError("Cabinet must be wider than two side panels")
        if not 0 < self.dado_depth_mm < self.plywood_mm:
            raise ValueError("Dado depth must be between zero and plywood thickness")
        if not 0 <= self.end_clearance_mm < self.dado_depth_mm:
            raise ValueError("End clearance must be nonnegative and less than dado depth")

    @property
    def shelf_length_mm(self) -> float:
        return self._parameter('Cab_Shelf_Length')

    @property
    def shelf_start_x_mm(self) -> float:
        return self._parameter('Cab_Shelf_X')

    @property
    def insertion_each_end_mm(self) -> float:
        self.validate()
        operation = _reference_assembly().operations[0]
        env = self._environment()
        return operation.groove_depth.eval(env) - operation.end_clearance.eval(env)

    def _environment(self):
        return {'Cab_Width': self.cabinet_width_mm, 'Cab_Ply': self.plywood_mm,
                'Cab_Dado_Depth': self.dado_depth_mm, 'Cab_End_Clearance': self.end_clearance_mm}

    def _parameter(self, name):
        self.validate()
        parameter = next(p for p in _reference_assembly().parameters.derived() if p.name == name)
        return parameter.expr.eval(self._environment())
