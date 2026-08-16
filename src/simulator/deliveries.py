from __future__ import annotations

import csv
import math
import random
from pathlib import Path


TRAFFIC_CONDITIONS = [
    "LOW",
    "MODERATE",
    "HIGH",
    "SEVERE",
]

WEATHER_CONDITIONS = [
    "CLEAR",
    "CLOUDY",
    "RAIN",
]


def parse_float(value: str) -> float:
    """Convert a CSV value into float."""
    return float(value)


def calculate_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculate approximate straight-line distance using the Haversine formula.

    A road-distance multiplier is then applied because straight-line
    distance is normally shorter than the actual delivery route.
    """
    earth_radius_km = 6371.0

    lat1 = math.radians(latitude_1)
    lat2 = math.radians(latitude_2)

    delta_lat = math.radians(latitude_2 - latitude_1)
    delta_lon = math.radians(longitude_2 - longitude_1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    straight_line_distance = earth_radius_km * c

    # Approximate road-route adjustment.
    road_factor = random.uniform(1.15, 1.40)

    return round(
        straight_line_distance * road_factor,
        2,
    )


def choose_traffic_condition() -> str:
    """Generate a weighted traffic condition."""
    return random.choices(
        population=TRAFFIC_CONDITIONS,
        weights=[20, 45, 25, 10],
        k=1,
    )[0]


def choose_weather_condition() -> str:
    """Generate a weighted weather condition."""
    return random.choices(
        population=WEATHER_CONDITIONS,
        weights=[65, 25, 10],
        k=1,
    )[0]


def generate_deliveries(
    fulfilment_units: list[dict],
    stores: list[dict],
    orders: list[dict],
) -> list[dict]:
    """
    Generate delivery requests for active fulfilment units.

    A delivery request exists before a rider accepts it.
    Therefore rider_id remains empty at this stage.
    """
    if not fulfilment_units:
        raise ValueError("Fulfilment units cannot be empty.")

    if not stores:
        raise ValueError("Stores cannot be empty.")

    if not orders:
        raise ValueError("Orders cannot be empty.")

    stores_by_id = {
        store["store_id"]: store
        for store in stores
    }

    orders_by_id = {
        order["order_id"]: order
        for order in orders
    }

    deliveries = []
    delivery_counter = 1

    for fulfilment in fulfilment_units:

        # Cancelled/failed fulfilments do not create a delivery.
        if fulfilment["status"] in {"CANCELLED", "FAILED"}:
            continue

        order = orders_by_id.get(fulfilment["order_id"])
        store = stores_by_id.get(fulfilment["store_id"])

        if order is None:
            raise ValueError(
                f"Order not found: {fulfilment['order_id']}"
            )

        if store is None:
            raise ValueError(
                f"Store not found: {fulfilment['store_id']}"
            )

        store_latitude = parse_float(store["latitude"])
        store_longitude = parse_float(store["longitude"])

        customer_latitude = parse_float(
            order["delivery_latitude"]
        )
        customer_longitude = parse_float(
            order["delivery_longitude"]
        )

        distance_km = calculate_distance_km(
            latitude_1=store_latitude,
            longitude_1=store_longitude,
            latitude_2=customer_latitude,
            longitude_2=customer_longitude,
        )

        traffic_condition = choose_traffic_condition()
        weather_condition = choose_weather_condition()

        deliveries.append(
            {
                "delivery_id": f"DEL-{delivery_counter:06d}",
                "fulfilment_unit_id": (
                    fulfilment["fulfilment_unit_id"]
                ),
                "rider_id": "",
                "status": "REQUESTED",
                "rider_arrived_at_store": "",
                "picked_up_at": "",
                "delivery_started_at": "",
                "delivered_at": "",
                "delivery_distance": distance_km,
                "traffic_condition": traffic_condition,
                "weather_condition": weather_condition,
                "cancelled_at": "",
                "cancellation_reason": "",
                "failed_at": "",
                "failure_reason": "",
            }
        )

        delivery_counter += 1

    return deliveries


def save_deliveries(
    deliveries: list[dict],
) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "deliveries.csv"

    fieldnames = [
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
        writer.writerows(deliveries)

    print(f"Generated {len(deliveries)} deliveries")
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
    fulfilment_units = load_csv(
        "fulfilment_units.csv"
    )

    stores = load_csv(
        "stores.csv"
    )

    orders = load_csv(
        "orders.csv"
    )

    deliveries = generate_deliveries(
        fulfilment_units=fulfilment_units,
        stores=stores,
        orders=orders,
    )

    save_deliveries(deliveries)