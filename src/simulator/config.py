from dataclasses import dataclass


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

    staffing_interval_hours: int = 1
    staffing_hours: int = 24

    # ---------------------------------------------------------
    # Operational SLA
    # ---------------------------------------------------------

    sla_target_minutes: int = 20
    sla_grace_minutes: int = 5


CONFIG = SimulationConfig()