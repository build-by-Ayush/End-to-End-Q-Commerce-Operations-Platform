from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from simulator.geography import BENGALURU_ZONES
from simulator.time_utils import format_timestamp


def generate_order_created_at(
    base_date: datetime,
) -> datetime:
    """
    Generate an order timestamp with realistic demand variation.

    Higher activity is concentrated around common quick-commerce
    demand periods.
    """

    demand_periods = [
        (7, 10),    # Morning
        (11, 14),   # Lunch
        (17, 22),   # Evening
        (22, 24),   # Late night
    ]

    start_hour, end_hour = random.choice(
        demand_periods
    )

    hour = random.randint(
        start_hour,
        end_hour - 1,
    )

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return base_date.replace(
        hour=hour,
        minute=minute,
        second=second,
    )


def generate_alternate_delivery_location(
    customer: dict,
) -> dict:
    """
    Generate an alternate delivery location.

    This simulates cases where a customer places an order
    for delivery somewhere other than their registered location.
    """

    zone = random.choice(BENGALURU_ZONES)

    latitude = round(
        zone.center_lat
        + random.uniform(
            -zone.spread,
            zone.spread,
        ),
        6,
    )

    longitude = round(
        zone.center_lon
        + random.uniform(
            -zone.spread,
            zone.spread,
        ),
        6,
    )

    return {
        "zone_id": zone.zone_id,
        "latitude": latitude,
        "longitude": longitude,
    }


def generate_orders(
    customers: list[dict],
    count: int = 100,
    base_date: datetime | None = None,
) -> list[dict]:
    """
    Generate order records using existing customers.

    Orders are created in the CREATED state.

    Final outcomes such as DELIVERED, CANCELLED, and FAILED
    are determined later by the operational lifecycle.
    """

    if not customers:
        raise ValueError(
            "Customers cannot be empty."
        )

    if count <= 0:
        raise ValueError(
            "Order count must be greater than zero."
        )

    if base_date is None:
        base_date = datetime(
            2026,
            8,
            15,
            0,
            0,
            0,
        )

    orders = []

    for i in range(1, count + 1):

        customer = random.choice(
            customers
        )

        created_at = generate_order_created_at(
            base_date
        )

        payment_success_at = (
            created_at
            + timedelta(
                seconds=random.randint(
                    5,
                    45,
                )
            )
        )

        # Most orders use the customer's registered
        # delivery location. A smaller percentage are
        # delivered to an alternate location.
        use_alternate_location = (
            random.random() < 0.10
        )

        if use_alternate_location:

            delivery_location = (
                generate_alternate_delivery_location(
                    customer
                )
            )

        else:

            delivery_location = {
                "zone_id": customer["zone_id"],
                "latitude": customer["latitude"],
                "longitude": customer["longitude"],
            }

        orders.append(
            {
                "order_id": f"ORD-{i:06d}",
                "customer_id": customer["customer_id"],
                "created_at": format_timestamp(
                    created_at
                ),
                "payment_success_at": format_timestamp(
                    payment_success_at
                ),
                "delivery_latitude": (
                    delivery_location["latitude"]
                ),
                "delivery_longitude": (
                    delivery_location["longitude"]
                ),
                "delivery_zone": (
                    delivery_location["zone_id"]
                ),

                # Status represents the current state.
                # At creation time the order has only just
                # been created.
                "status": "CREATED",

                # These are populated only if a later
                # lifecycle outcome requires them.
                "cancelled_at": "",
                "cancellation_reason": "",
                "failure_reason": "",
            }
        )

    return orders


def save_orders(
    orders: list[dict],
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
        output_dir / "orders.csv"
    )

    fieldnames = [
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
        writer.writerows(orders)

    print(
        f"Generated {len(orders)} orders"
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

    customers = load_csv(
        "customers.csv"
    )

    orders = generate_orders(
        customers=customers,
        count=100,
    )

    save_orders(orders)