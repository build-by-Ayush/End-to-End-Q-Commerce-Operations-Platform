from dataclasses import dataclass


@dataclass
class SimulationConfig:
    # Root entity counts
    customers: int = 100
    stores: int = 20
    riders: int = 50

    # Transaction volume
    orders: int = 100

    # Product pool
    products: int = 100

    # Store staffing
    staffing_interval_hours: int = 1


CONFIG = SimulationConfig()