from __future__ import annotations

from simulator.config import CONFIG
from simulator.state import SimulationState

from simulator.customers import generate_customers
from simulator.stores import generate_stores
from simulator.riders import generate_riders
from simulator.orders import generate_orders
from simulator.fulfilment_units import generate_fulfilment_units
from simulator.order_items import generate_order_items
from simulator.deliveries import generate_deliveries
from simulator.rider_assignments import generate_rider_assignments
from simulator.operational_events import generate_operational_events
from simulator.store_staffing import generate_store_staffing


def run_simulation() -> SimulationState:
    """
    Execute the simulator in dependency order.

    Each generator produces data that is stored in the shared
    SimulationState object for downstream generators to consume.
    """

    state = SimulationState()

    print("=" * 60)
    print("Starting Q-Commerce Simulation")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Reference data
    # ---------------------------------------------------------

    print("\n[1/10] Generating customers...")
    state.customers = generate_customers(
        CONFIG.customers
    )

    print(f"Generated {len(state.customers)} customers")

    print("\n[2/10] Generating stores...")
    state.stores = generate_stores(
        CONFIG.stores
    )

    print(f"Generated {len(state.stores)} stores")

    print("\n[3/10] Generating riders...")
    state.riders = generate_riders(
        CONFIG.riders
    )

    print(f"Generated {len(state.riders)} riders")

    # ---------------------------------------------------------
    # 2. Transactions
    # ---------------------------------------------------------

    print("\n[4/10] Generating orders...")
    state.orders = generate_orders(
        customers=state.customers,
        count=CONFIG.orders,
    )

    print(f"Generated {len(state.orders)} orders")

    print("\n[5/10] Generating fulfilment units...")
    state.fulfilment_units = generate_fulfilment_units(
        orders=state.orders,
        stores=state.stores,
    )

    print(
        f"Generated {len(state.fulfilment_units)} "
        "fulfilment units"
    )

    print("\n[6/10] Generating order items...")
    state.order_items = generate_order_items(
        orders=state.orders,
        fulfilment_units=state.fulfilment_units,
    )

    print(
        f"Generated {len(state.order_items)} "
        "order items"
    )

    print("\n[7/10] Generating deliveries...")
    state.deliveries = generate_deliveries(
        fulfilment_units=state.fulfilment_units,
        stores=state.stores,
        orders=state.orders,
    )

    print(
        f"Generated {len(state.deliveries)} "
        "deliveries"
    )

    print("\n[8/10] Generating rider assignments...")

    assignments, updated_deliveries = (
        generate_rider_assignments(
            deliveries=state.deliveries,
            riders=state.riders,
            fulfilment_units=state.fulfilment_units,
        )
    )

    state.rider_assignments = assignments
    state.deliveries = updated_deliveries

    print(
        f"Generated {len(state.rider_assignments)} "
        "rider assignments"
    )

    # ---------------------------------------------------------
    # 3. Operational timeline
    # ---------------------------------------------------------

    print("\n[9/10] Generating operational events...")

    (
        state.operational_events,
        state.fulfilment_units,
        state.deliveries,
    ) = generate_operational_events(
        orders=state.orders,
        fulfilment_units=state.fulfilment_units,
        deliveries=state.deliveries,
        assignments=state.rider_assignments,
    )

    print(
        f"Generated {len(state.operational_events)} "
        "operational events"
    )

    # ---------------------------------------------------------
    # 4. Store staffing
    # ---------------------------------------------------------

    print("\n[10/10] Generating store staffing...")

    # Temporary development date.
    # We will move this into SimulationConfig later.
    from datetime import datetime

    state.store_staffing = generate_store_staffing(
        stores=state.stores,
        start_datetime=datetime(
            2026,
            8,
            15,
            0,
            0,
            0,
        ),
        hours=24,
    )

    print(
        f"Generated {len(state.store_staffing)} "
        "staffing observations"
    )

    print("\n" + "=" * 60)
    print("Simulation completed")
    print("=" * 60)

    return state


if __name__ == "__main__":
    run_simulation()