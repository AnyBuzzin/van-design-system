"""Unit-explicit CAD-neutral shelf and dado formula references."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DadoShelf:
    cabinet_width_mm: float
    plywood_mm: float
    dado_depth_mm: float
    end_clearance_mm: float

    def validate(self) -> None:
        if self.cabinet_width_mm <= 2 * self.plywood_mm:
            raise ValueError("Cabinet must be wider than two side panels")
        if not 0 < self.dado_depth_mm < self.plywood_mm:
            raise ValueError("Dado depth must be between zero and plywood thickness")
        if not 0 <= self.end_clearance_mm < self.dado_depth_mm:
            raise ValueError("End clearance must be nonnegative and less than dado depth")

    @property
    def shelf_length_mm(self) -> float:
        self.validate()
        return self.cabinet_width_mm - 2 * self.plywood_mm + 2 * (self.dado_depth_mm - self.end_clearance_mm)

    @property
    def shelf_start_x_mm(self) -> float:
        self.validate()
        return self.plywood_mm - self.dado_depth_mm + self.end_clearance_mm

    @property
    def insertion_each_end_mm(self) -> float:
        self.validate()
        return self.dado_depth_mm - self.end_clearance_mm
