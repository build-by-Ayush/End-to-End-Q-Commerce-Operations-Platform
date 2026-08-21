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
) -> list[dict]:
    """
    Generate item lines for orders.

    Each order receives a basket of 1-10 distinct item lines.
    Every item line is assigned to one fulfilment unit belonging
    to the same parent order.
    """
    if not orders:
        raise ValueError("Orders cannot be empty.")

    if not fulfilment_units:
        raise ValueError("Fulfilment units cannot be empty.")

    # Group fulfilment units by order for fast lookup.
    fulfilments_by_order: dict[str, list[dict]] = {}

    for fulfilment in fulfilment_units:
        order_id = fulfilment["order_id"]

        fulfilments_by_order.setdefault(order_id, []).append(
            fulfilment
        )

    order_items = []
    item_counter = 1

    for order in orders:
        order_id = order["order_id"]

        units = fulfilments_by_order.get(order_id)

        # Cancelled/failed orders may have no fulfilment unit.
        if not units:
            continue

        # Only use fulfilment units that are actually progressing.
        active_units = [
            unit
            for unit in units
            if unit["status"] == "PENDING"
        ]

        if not active_units:
            continue

        # Basket size is generated at the order level.
        item_line_count = random.randint(1, 10)

        selected_products = random.sample(
            PRODUCT_IDS,
            k=min(item_line_count, len(PRODUCT_IDS)),
        )

        for product_id in selected_products:
            fulfilment_unit = random.choice(active_units)

            quantity = random.choices(
                population=[1, 2, 3, 4],
                weights=[60, 25, 10, 5],
                k=1,
            )[0]

            order_items.append(
                {
                    "order_item_id": f"OI-{item_counter:07d}",
                    "order_id": order_id,
                    "fulfilment_unit_id": (
                        fulfilment_unit["fulfilment_unit_id"]
                    ),
                    "product_id": product_id,
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