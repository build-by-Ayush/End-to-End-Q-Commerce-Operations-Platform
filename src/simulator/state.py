from dataclasses import dataclass, field


@dataclass
class SimulationState:
    customers: list[dict] = field(default_factory=list)
    stores: list[dict] = field(default_factory=list)
    riders: list[dict] = field(default_factory=list)

    orders: list[dict] = field(default_factory=list)
    order_items: list[dict] = field(default_factory=list)
    fulfilment_units: list[dict] = field(default_factory=list)

    deliveries: list[dict] = field(default_factory=list)
    rider_assignments: list[dict] = field(default_factory=list)

    operational_events: list[dict] = field(default_factory=list)
    store_staffing: list[dict] = field(default_factory=list)