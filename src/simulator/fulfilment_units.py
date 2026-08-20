from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


def parse_datetime(
    value: str,
) -> datetime:
    return datetime.strptime(
        value,
        "%Y-%m-%d %H:%M:%S",
    )


def choose_store(
    order: dict,
    stores: list[dict],
) -> dict:
    """
    Select an active store in the order's delivery zone.

    Same-zone stores are preferred.
    """

    same_zone_stores = [
        store
        for store in stores
        if (
            store["zone"]
            == order["delivery_zone"]
            and store["status"]
            == "ACTIVE"
        )
    ]

    if same_zone_stores:
        return random.choice(
            same_zone_stores
        )

    active_stores = [
        store
        for store in stores
        if store["status"] == "ACTIVE"
    ]

    if not active_stores:
        raise ValueError(
            "No active stores available."
        )

    return random.choice(
        active_stores
    )


def choose_second_store(
    first_store: dict,
    order: dict,
    stores: list[dict],
) -> dict | None:
    """
    Choose another active store in the same
    delivery zone for split fulfilment.
    """

    alternatives = [
        store
        for store in stores
        if (
            store["store_id"]
            != first_store["store_id"]
            and store["status"]
            == "ACTIVE"
            and store["zone"]
            == order["delivery_zone"]
        )
    ]

    if not alternatives:
        return None

    return random.choice(
        alternatives
    )


def generate_fulfilment_units(
    orders: list[dict],
    stores: list[dict],
) -> list[dict]:

    if not orders:
        raise ValueError(
            "Orders cannot be empty."
        )

    if not stores:
        raise ValueError(
            "Stores cannot be empty."
        )

    fulfilment_units = []

    unit_counter = 1

    for order in orders:

        # At this stage every generated order has
        # entered the logistics flow.
        first_store = choose_store(
            order,
            stores,
        )

        assigned_at = (
            parse_datetime(
                order["payment_success_at"]
            )
            + timedelta(
                seconds=random.randint(
                    30,
                    120,
                )
            )
        )

        # Approximately 10% of orders are split.
        split_order = (
            random.random() < 0.10
        )

        selected_stores = [
            first_store
        ]

        if split_order:

            second_store = (
                choose_second_store(
                    first_store=first_store,
                    order=order,
                    stores=stores,
                )
            )

            if second_store is not None:
                selected_stores.append(
                    second_store
                )

        for store in selected_stores:

            fulfilment_unit_id = (
                f"FU-{unit_counter:06d}"
            )

            unit_counter += 1

            fulfilment_units.append(
                {
                    "fulfilment_unit_id": (
                        fulfilment_unit_id
                    ),
                    "order_id": (
                        order["order_id"]
                    ),
                    "store_id": (
                        store["store_id"]
                    ),

                    # The lifecycle engine will
                    # update this later.
                    "status": "PENDING",

                    "assigned_to_store_at": (
                        assigned_at.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    ),

                    "picking_started_at": "",
                    "picking_completed_at": "",
                    "packing_started_at": "",
                    "packing_completed_at": "",

                    "cancelled_at": "",
                    "cancellation_reason": "",

                    "failed_at": "",
                    "failure_reason": "",

                    # This must remain empty until
                    # the actual fulfilment lifecycle
                    # reaches completion.
                    "completed_at": "",
                }
            )

    return fulfilment_units


def save_fulfilment_units(
    fulfilment_units: list[dict],
) -> None:

    output_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        output_dir
        / "fulfilment_units.csv"
    )

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
        writer.writerows(
            fulfilment_units
        )

    print(
        f"Generated "
        f"{len(fulfilment_units)} "
        "fulfilment units"
    )

    print(
        f"Dataset saved to: {output_file}"
    )


def load_csv(
    filename: str,
) -> list[dict]:

    dataset_dir = (
        Path(__file__).parent.parent
        / "datasets"
    )

    input_file = (
        dataset_dir / filename
    )

    if not input_file.exists():
        raise FileNotFoundError(
            f"Required dataset not found: "
            f"{input_file}"
        )

    with input_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:

        return list(
            csv.DictReader(file)
        )


if __name__ == "__main__":

    orders = load_csv(
        "orders.csv"
    )

    stores = load_csv(
        "stores.csv"
    )

    fulfilment_units = (
        generate_fulfilment_units(
            orders=orders,
            stores=stores,
        )
    )

    save_fulfilment_units(
        fulfilment_units
    )