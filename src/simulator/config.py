from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SimulationConfig:
    # ---------------------------------------------------------
    # Root / reference data
    # ---------------------------------------------------------

    customers: int = 1_000_000
    stores: int = 120
    riders: int = 2_000

    # ---------------------------------------------------------
    # Transaction volume
    # ---------------------------------------------------------

    orders: int = 500_000

    # ---------------------------------------------------------
    # Lightweight product reference pool
    # ---------------------------------------------------------

    products: int = 100

    # ---------------------------------------------------------
    # Simulation period / staffing
    # ---------------------------------------------------------

    simulation_start: datetime = datetime(2026, 8, 15, 0, 0, 0)
    simulation_days: int = 30
    staffing_interval_hours: int = 1

    # Leave sufficient time at the end of the calendar for an
    # order's operational lifecycle to finish inside the period.
    lifecycle_buffer_minutes: int = 90

    # A seeded run is reproducible, which makes operational changes
    # and validation results comparable.
    random_seed: int = 2026

    # ---------------------------------------------------------
    # Operational SLA
    # ---------------------------------------------------------

    sla_target_minutes: int = 20
    sla_grace_minutes: int = 5

    @property
    def simulation_end(self) -> datetime:
        return self.simulation_start + timedelta(
            days=self.simulation_days
        )

    @property
    def simulation_hours(self) -> int:
        return self.simulation_days * 24


CONFIG = SimulationConfig()
