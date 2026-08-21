from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from simulator.config import CONFIG
from simulator.state import SimulationState

from simulator.customers import generate_customers
from simulator.stores import generate_stores
from simulator.riders import generate_riders
from simulator.orders import generate_orders
from simulator.fulfilment_units import generate_fulfilment_units
from simulator.order_items import generate_order_items
from simulator.deliveries import generate_deliveries
from simulator.rider_assignments import (
    generate_assignment_attempts,
)
from simulator.operational_events import (
    generate_operational_events,
)
from simulator.store_staffing import (
    generate_store_staffing,
)


DATASET_DIR = (
    Path(__file__).parent.parent / "datasets"
)


def save_csv(
    filename: str,
    rows: list[dict],
    fieldnames: list[str],
) -> None:
    """
    Save a list of dictionaries to a CSV file.
    """

    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        DATASET_DIR / filename
    )

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def save_all_datasets(
    state: SimulationState,
) -> None:
    """
    Save the completed SimulationState to CSV files.

    This is the only place where the central simulator
    writes its final datasets.
    """

    save_csv(
        "customers.csv",
        state.customers,
        [
            "customer_id",
            "zone_id",
            "latitude",
            "longitude",
        ],
    )

    save_csv(
        "stores.csv",
        state.stores,
        [
            "store_id",
            "store_name",
            "zone",
            "latitude",
            "longitude",
            "baseline_capacity",
            "status",
            "opened_at",
            "closed_at",
        ],
    )

    save_csv(
        "riders.csv",
        state.riders,
        [
            "rider_id",
            "vehicle_type",
            "home_zone",
            "status",
            "joined_at",
            "deactivated_at",
        ],
    )

    save_csv(
        "orders.csv",
        state.orders,
        [
            "order_id",
            "customer_id",
            "created_at",
            "payment_success_at",
            "delivery_latitude",
            "delivery_longitude",
            "delivery_zone",
            "status",
            "cancelled_at",
            "cancellation_reason",
            "failure_reason",
        ],
    )

    save_csv(
        "fulfilment_units.csv",
        state.fulfilment_units,
        [
            "fulfilment_unit_id",
            "order_id",
            "store_id",
            "status",
            "assigned_to_store_at",
            "picking_started_at",
            "picking_completed_at",
            "packing_started_at",
            "packing_completed_at",
            "cancelled_at",
            "cancellation_reason",
            "failed_at",
            "failure_reason",
            "completed_at",
        ],
    )

    save_csv(
        "order_items.csv",
        state.order_items,
        [
            "order_item_id",
            "order_id",
            "fulfilment_unit_id",
            "product_id",
            "quantity",
        ],
    )

    save_csv(
        "deliveries.csv",
        state.deliveries,
        [
            "delivery_id",
            "fulfilment_unit_id",
            "rider_id",
            "status",
            "rider_arrived_at_store",
            "picked_up_at",
            "delivery_started_at",
            "delivered_at",
            "delivery_distance",
            "traffic_condition",
            "weather_condition",
            "cancelled_at",
            "cancellation_reason",
            "failed_at",
            "failure_reason",
        ],
    )

    save_csv(
        "rider_assignments.csv",
        state.rider_assignments,
        [
            "assignment_id",
            "delivery_id",
            "rider_id",
            "offered_at",
            "responded_at",
            "expired_at",
            "response",
            "rejection_reason",
        ],
    )

    save_csv(
        "operational_events.csv",
        state.operational_events,
        [
            "event_id",
            "event_type",
            "occurred_at",
            "order_id",
            "fulfilment_unit_id",
            "delivery_id",
            "store_id",
            "rider_id",
            "reason",
        ],
    )

    save_csv(
        "store_staffing.csv",
        state.store_staffing,
        [
            "staffing_snapshot_id",
            "store_id",
            "recorded_at",
            "pickers_scheduled",
            "pickers_available",
            "packers_scheduled",
            "packers_available",
        ],
    )

    print(
        "\nAll datasets saved successfully."
    )
    print(
        f"Output directory: {DATASET_DIR}"
    )


def run_simulation() -> SimulationState:
    """
    Execute the complete simulator in dependency order.
    """

    state = SimulationState()

    print("=" * 60)
    print("Q-COMMERCE SIMULATION")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Root/reference data
    # ---------------------------------------------------------

    print("\n[1/10] Customers")

    state.customers = generate_customers(
        CONFIG.customers
    )

    print(
        f"  Generated: "
        f"{len(state.customers):,}"
    )

    print("\n[2/10] Stores")

    state.stores = generate_stores(
        CONFIG.stores
    )

    print(
        f"  Generated: "
        f"{len(state.stores):,}"
    )

    print("\n[3/10] Riders")

    state.riders = generate_riders(
        CONFIG.riders
    )

    print(
        f"  Generated: "
        f"{len(state.riders):,}"
    )

    # ---------------------------------------------------------
    # 2. Transaction generation
    # ---------------------------------------------------------

    print("\n[4/10] Orders")

    state.orders = generate_orders(
        customers=state.customers,
        count=CONFIG.orders,
    )

    print(
        f"  Generated: "
        f"{len(state.orders):,}"
    )

    print("\n[5/10] Fulfilment Units")

    state.fulfilment_units = (
        generate_fulfilment_units(
            orders=state.orders,
            stores=state.stores,
        )
    )

    print(
        f"  Generated: "
        f"{len(state.fulfilment_units):,}"
    )

    print("\n[6/10] Order Items")

    state.order_items = (
        generate_order_items(
            orders=state.orders,
            fulfilment_units=(
                state.fulfilment_units
            ),
        )
    )

    print(
        f"  Generated: "
        f"{len(state.order_items):,}"
    )

    print("\n[7/10] Deliveries")

    state.deliveries = (
        generate_deliveries(
            fulfilment_units=(
                state.fulfilment_units
            ),
            stores=state.stores,
            orders=state.orders,
        )
    )

    print(
        f"  Generated: "
        f"{len(state.deliveries):,}"
    )

    # ---------------------------------------------------------
    # 3. Lifecycle engine
    # ---------------------------------------------------------

    print("\n[9/10] Operational Lifecycle")

    (
        state.operational_events,
        state.orders,
        state.fulfilment_units,
        state.deliveries,
        state.rider_assignments,
    ) = generate_operational_events(
        orders=state.orders,
        fulfilment_units=(
            state.fulfilment_units
        ),
        deliveries=state.deliveries,
        riders=state.riders,
        stores=state.stores,
    )

    print(
        f"  Generated: "
        f"{len(state.operational_events):,} "
        "events"
    )

    # ---------------------------------------------------------
    # 4. Store staffing
    # ---------------------------------------------------------

    print("\n[10/10] Store Staffing")

    state.store_staffing = (
        generate_store_staffing(
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
    )

    print(
        f"  Generated: "
        f"{len(state.store_staffing):,}"
    )

    # ---------------------------------------------------------
    # Save final state
    # ---------------------------------------------------------

    print("\n" + "-" * 60)
    print("Saving final datasets...")
    print("-" * 60)

    save_all_datasets(state)

    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)

    return state


if __name__ == "__main__":
    run_simulation()