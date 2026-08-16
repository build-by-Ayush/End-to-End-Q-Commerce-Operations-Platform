from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


ORDER_STATUSES = [
    "FULFILLING",
    "DELIVERED",
    "CANCELLED",
    "FAILED",
]


def generate_order_created_at() -> datetime:
    """
    Generate an order timestamp with realistic demand variation.

    More orders are generated during common quick-commerce
    demand periods rather than uniformly across the day.
    """
    demand_periods = [
        (7, 10),    # Morning
        (11, 14),   # Lunch
        (17, 22),   # Evening
        (22, 24),   # Late night
    ]

    start_hour, end_hour = random.choice(demand_periods)

    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    base_date = datetime(2026, 8, 15)

    return base_date.replace(
        hour=hour,
        minute=minute,
        second=second,
    )


def generate_orders(
    customers: list[dict],
    count: int = 100,
) -> list[dict]:
    """
    Generate orders using existing customers.

    Each order references a real customer and copies the customer's
    current location into the order as a historical delivery snapshot.
    """
    if not customers:
        raise ValueError("Customers cannot be empty.")

    orders = []

    for i in range(1, count + 1):
        customer = random.choice(customers)

        created_at = generate_order_created_at()

        # Payment usually succeeds shortly after order creation.
        payment_success_at = created_at + timedelta(
            seconds=random.randint(5, 45)
        )

        status = random.choices(
            population=ORDER_STATUSES,
            weights=[70, 20, 7, 3],
            k=1,
        )[0]

        cancelled_at = None
        cancellation_reason = None
        failure_reason = None

        if status == "CANCELLED":
            cancelled_at = payment_success_at + timedelta(
                minutes=random.randint(2, 20)
            )
            cancellation_reason = random.choice(
                [
                    "CUSTOMER_REQUEST",
                    "PAYMENT_ISSUE",
                    "STORE_UNAVAILABLE",
                    "ITEM_UNAVAILABLE",
                ]
            )

        elif status == "FAILED":
            failure_reason = random.choice(
                [
                    "STORE_ASSIGNMENT_FAILED",
                    "SYSTEM_ERROR",
                    "NO_RIDER_AVAILABLE",
                ]
            )

        orders.append(
            {
                "order_id": f"ORD-{i:06d}",
                "customer_id": customer["customer_id"],
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "payment_success_at": payment_success_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "delivery_latitude": customer["latitude"],
                "delivery_longitude": customer["longitude"],
                "delivery_zone": customer["zone_id"],
                "status": status,
                "cancelled_at": (
                    cancelled_at.strftime("%Y-%m-%d %H:%M:%S")
                    if cancelled_at
                    else ""
                ),
                "cancellation_reason": cancellation_reason or "",
                "failure_reason": failure_reason or "",
            }
        )

    return orders


def save_orders(orders: list[dict]) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "orders.csv"

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
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(orders)

    print(f"Generated {len(orders)} orders")
    print(f"Dataset saved to: {output_file}")


if __name__ == "__main__":
    # Load the existing customer dataset.
    customers_file = (
        Path(__file__).parent.parent
        / "datasets"
        / "customers.csv"
    )

    with customers_file.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        customers = list(csv.DictReader(file))

    orders = generate_orders(
        customers=customers,
        count=100,
    )

    save_orders(orders)