from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


FULFILMENT_STATUSES = [
    "READY_FOR_PICKING",
    "CANCELLED",
    "FAILED",
]


def parse_datetime(value: str) -> datetime:
    """Convert CSV timestamp text into a datetime object."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def choose_store(
    order: dict,
    stores: list[dict],
) -> dict:
    """
    Select a store for an order.

    First preference:
        Store operating in the same zone as the customer/order.

    Fallback:
        Any active store.
    """
    same_zone_stores = [
        store
        for store in stores
        if store["zone"] == order["delivery_zone"]
        and store["status"] == "ACTIVE"
    ]

    if same_zone_stores:
        return random.choice(same_zone_stores)

    active_stores = [
        store
        for store in stores
        if store["status"] == "ACTIVE"
    ]

    if not active_stores:
        raise ValueError("No active stores available.")

    return random.choice(active_stores)


def choose_second_store(
    first_store: dict,
    order: dict,
    stores: list[dict],
) -> dict | None:
    """
    Choose a second store for a split fulfilment.

    Prefer a different store in the same zone.
    """
    alternatives = [
        store
        for store in stores
        if (
            store["store_id"] != first_store["store_id"]
            and store["status"] == "ACTIVE"
            and store["zone"] == order["delivery_zone"]
        )
    ]

    if not alternatives:
        return None

    return random.choice(alternatives)


def generate_fulfilment_units(
    orders: list[dict],
    stores: list[dict],
) -> list[dict]:
    """
    Generate one or more fulfilment units for each eligible order.
    """
    if not orders:
        raise ValueError("Orders cannot be empty.")

    if not stores:
        raise ValueError("Stores cannot be empty.")

    fulfilment_units = []
    unit_counter = 1

    for order in orders:
        # Orders that are already cancelled or failed do not proceed
        # into normal fulfilment.
        if order["status"] in {"CANCELLED", "FAILED"}:
            continue

        first_store = choose_store(order, stores)

        assigned_at = parse_datetime(order["payment_success_at"]) + timedelta(
            seconds=random.randint(30, 120)
        )

        # Most orders use one store.
        split_order = random.random() < 0.10

        selected_stores = [first_store]

        if split_order:
            second_store = choose_second_store(
                first_store=first_store,
                order=order,
                stores=stores,
            )

            if second_store:
                selected_stores.append(second_store)

        for store in selected_stores:
            fulfilment_unit_id = f"FU-{unit_counter:06d}"
            unit_counter += 1

            status = random.choices(
                population=FULFILMENT_STATUSES,
                weights=[94, 4, 2],
                k=1,
            )[0]

            cancelled_at = None
            cancellation_reason = None
            failed_at = None
            failure_reason = None
            completed_at = None

            if status == "CANCELLED":
                cancelled_at = assigned_at + timedelta(
                    minutes=random.randint(1, 5)
                )

                cancellation_reason = random.choice(
                    [
                        "STORE_UNAVAILABLE",
                        "CUSTOMER_REQUEST",
                        "ITEM_UNAVAILABLE",
                    ]
                )

            elif status == "FAILED":
                failed_at = assigned_at + timedelta(
                    minutes=random.randint(1, 5)
                )

                failure_reason = random.choice(
                    [
                        "STORE_CAPACITY_EXCEEDED",
                        "STORE_OPERATIONAL_FAILURE",
                        "ITEM_UNAVAILABLE",
                    ]
                )

            else:
                completed_at = assigned_at + timedelta(
                    minutes=random.randint(2, 8)
                )

            fulfilment_units.append(
                {
                    "fulfilment_unit_id": fulfilment_unit_id,
                    "order_id": order["order_id"],
                    "store_id": store["store_id"],
                    "status": status,
                    "assigned_to_store_at": assigned_at.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "picking_started_at": "",
                    "picking_completed_at": "",
                    "packing_started_at": "",
                    "packing_completed_at": "",
                    "cancelled_at": (
                        cancelled_at.strftime("%Y-%m-%d %H:%M:%S")
                        if cancelled_at
                        else ""
                    ),
                    "cancellation_reason": cancellation_reason or "",
                    "failed_at": (
                        failed_at.strftime("%Y-%m-%d %H:%M:%S")
                        if failed_at
                        else ""
                    ),
                    "failure_reason": failure_reason or "",
                    "completed_at": (
                        completed_at.strftime("%Y-%m-%d %H:%M:%S")
                        if completed_at
                        else ""
                    ),
                }
            )

    return fulfilment_units


def save_fulfilment_units(
    fulfilment_units: list[dict],
) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "fulfilment_units.csv"

    fieldnames = [
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
    ]

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
        writer.writerows(fulfilment_units)

    print(f"Generated {len(fulfilment_units)} fulfilment units")
    print(f"Dataset saved to: {output_file}")


def load_csv(filename: str) -> list[dict]:
    """Load a simulator dataset from src/datasets."""
    dataset_dir = Path(__file__).parent.parent / "datasets"
    input_file = dataset_dir / filename

    if not input_file.exists():
        raise FileNotFoundError(
            f"Required dataset not found: {input_file}"
        )

    with input_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    orders = load_csv("orders.csv")
    stores = load_csv("stores.csv")

    fulfilment_units = generate_fulfilment_units(
        orders=orders,
        stores=stores,
    )

    save_fulfilment_units(fulfilment_units)