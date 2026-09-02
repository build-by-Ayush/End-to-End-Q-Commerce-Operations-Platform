from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from simulator.config import CONFIG
from simulator.geography import BENGALURU_ZONES
from simulator.time_utils import format_timestamp


HOURLY_DEMAND_WEIGHTS = {
    7: 5.5,
    8: 5.5,
    9: 5.0,
    10: 4.0,
    11: 6.0,
    12: 6.5,
    13: 6.5,
    14: 5.0,
    15: 4.0,
    16: 4.0,
    17: 5.5,
    18: 7.5,
    19: 8.0,
    20: 8.0,
    21: 7.0,
    22: 7.0,
    23: 5.0,
}

# Monday through Sunday. The values are relative rather than exact
# quotas; random sampling preserves daily variation while the caller
# controls the exact total order count.
WEEKDAY_DEMAND_WEIGHTS = [
    0.95,
    0.98,
    1.00,
    1.00,
    1.05,
    1.15,
    1.10,
]


def demand_multiplier_for_hour(hour: int) -> float:
    """Return the staffing multiplier implied by the order profile."""

    average_hourly_weight = sum(
        HOURLY_DEMAND_WEIGHTS.values()
    ) / 24

    return max(
        0.65,
        HOURLY_DEMAND_WEIGHTS.get(hour, 0.0)
        / average_hourly_weight,
    )


def demand_multiplier_for_date(value: datetime) -> float:
    """Return the planned weekday demand multiplier for a date."""

    return WEEKDAY_DEMAND_WEIGHTS[value.weekday()]


def generate_order_created_at(
    simulation_start: datetime,
    simulation_days: int,
    latest_created_at: datetime,
) -> datetime:
    """
    Generate an order timestamp with realistic demand variation.

    Higher activity is concentrated around common quick-commerce
    demand periods.
    """

    if simulation_days <= 0:
        raise ValueError(
            "simulation_days must be greater than zero."
        )

    day_offsets = list(range(simulation_days))
    day_weights = [
        demand_multiplier_for_date(
            simulation_start + timedelta(days=offset)
        )
        for offset in day_offsets
    ]

    hours = list(HOURLY_DEMAND_WEIGHTS)
    hour_weights = [
        HOURLY_DEMAND_WEIGHTS[hour]
        for hour in hours
    ]

    # The final-day cutoff prevents lifecycle timestamps from leaking
    # outside the centralized simulation calendar.
    while True:
        day_offset = random.choices(
            day_offsets,
            weights=day_weights,
            k=1,
        )[0]

        hour = random.choices(
            hours,
            weights=hour_weights,
            k=1,
        )[0]

        candidate = simulation_start + timedelta(
            days=day_offset,
            hours=hour,
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        if candidate <= latest_created_at:
            return candidate


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
    simulation_start: datetime | None = None,
    simulation_days: int | None = None,
    lifecycle_buffer_minutes: int | None = None,
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

    if simulation_start is None:
        simulation_start = CONFIG.simulation_start

    if simulation_days is None:
        simulation_days = CONFIG.simulation_days

    if lifecycle_buffer_minutes is None:
        lifecycle_buffer_minutes = (
            CONFIG.lifecycle_buffer_minutes
        )

    if lifecycle_buffer_minutes < 0:
        raise ValueError(
            "lifecycle_buffer_minutes cannot be negative."
        )

    simulation_end = simulation_start + timedelta(
        days=simulation_days
    )

    latest_created_at = simulation_end - timedelta(
        minutes=lifecycle_buffer_minutes
    )

    orders = []

    for i in range(1, count + 1):

        customer = random.choice(
            customers
        )

        created_at = generate_order_created_at(
            simulation_start=simulation_start,
            simulation_days=simulation_days,
            latest_created_at=latest_created_at,
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
