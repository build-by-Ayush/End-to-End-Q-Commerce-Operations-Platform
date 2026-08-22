from __future__ import annotations

import csv
import random
from pathlib import Path


PRODUCT_IDS = [
    "PROD-001",
    "PROD-002",
    "PROD-003",
    "PROD-004",
    "PROD-005",
    "PROD-006",
    "PROD-007",
    "PROD-008",
    "PROD-009",
    "PROD-010",
]


def generate_order_items(
    orders: list[dict],
    fulfilment_units: list[dict],
    product_count: int = 100,
) -> list[dict]:
    """
    Generate order-item rows while guaranteeing that every
    fulfilment unit receives at least one item.

    Each order item belongs to:
        one order
        one fulfilment unit
        one product
    """

    if not orders:
        raise ValueError(
            "Orders cannot be empty."
        )

    if not fulfilment_units:
        raise ValueError(
            "Fulfilment units cannot be empty."
        )

    if product_count <= 0:
        raise ValueError(
            "Product count must be greater than zero."
        )

    fulfilments_by_order: dict[
        str,
        list[dict],
    ] = {}

    for fulfilment in fulfilment_units:
        fulfilments_by_order.setdefault(
            fulfilment["order_id"],
            [],
        ).append(
            fulfilment
        )

    order_items: list[dict] = []
    item_counter = 1

    for order in orders:

        order_id = order["order_id"]

        order_fulfilments = (
            fulfilments_by_order.get(
                order_id,
                [],
            )
        )

        if not order_fulfilments:
            raise ValueError(
                f"No fulfilment units found for "
                f"order {order_id}"
            )

        # -----------------------------------------------------
        # Determine number of item lines.
        #
        # We need at least one item line per fulfilment unit.
        # -----------------------------------------------------

        minimum_items = len(
            order_fulfilments
        )

        additional_items = random.randint(
            0,
            6,
        )

        item_line_count = (
            minimum_items
            + additional_items
        )

        # -----------------------------------------------------
        # First guarantee one item per fulfilment unit.
        # -----------------------------------------------------

        assigned_fulfilments = (
            order_fulfilments.copy()
        )

        for fulfilment in assigned_fulfilments:

            product_number = random.randint(
                1,
                product_count,
            )

            quantity = random.randint(
                1,
                3,
            )

            order_items.append(
                {
                    "order_item_id": (
                        f"OI-{item_counter:07d}"
                    ),
                    "order_id": order_id,
                    "fulfilment_unit_id": (
                        fulfilment[
                            "fulfilment_unit_id"
                        ]
                    ),
                    "product_id": (
                        f"PROD-{product_number:03d}"
                    ),
                    "quantity": quantity,
                }
            )

            item_counter += 1

        # -----------------------------------------------------
        # Assign remaining item lines randomly.
        # -----------------------------------------------------

        remaining_items = (
            item_line_count
            - minimum_items
        )

        for _ in range(
            remaining_items
        ):

            fulfilment = random.choice(
                order_fulfilments
            )

            product_number = random.randint(
                1,
                product_count,
            )

            quantity = random.randint(
                1,
                3,
            )

            order_items.append(
                {
                    "order_item_id": (
                        f"OI-{item_counter:07d}"
                    ),
                    "order_id": order_id,
                    "fulfilment_unit_id": (
                        fulfilment[
                            "fulfilment_unit_id"
                        ]
                    ),
                    "product_id": (
                        f"PROD-{product_number:03d}"
                    ),
                    "quantity": quantity,
                }
            )

            item_counter += 1

    return order_items

def save_order_items(order_items: list[dict]) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "order_items.csv"

    fieldnames = [
        "order_item_id",
        "order_id",
        "fulfilment_unit_id",
        "product_id",
        "quantity",
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
        writer.writerows(order_items)

    print(f"Generated {len(order_items)} order items")
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
    fulfilment_units = load_csv("fulfilment_units.csv")

    order_items = generate_order_items(
        orders=orders,
        fulfilment_units=fulfilment_units,
    )

    save_order_items(order_items)