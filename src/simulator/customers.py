from __future__ import annotations

import csv
import random
from pathlib import Path

from simulator.geography import BENGALURU_ZONES


def generate_customers(count: int = 100) -> list[dict]:
    customers = []

    for i in range(1, count + 1):
        zone = random.choice(BENGALURU_ZONES)

        latitude = round(
            zone.center_lat + random.uniform(-zone.spread, zone.spread),
            6,
        )

        longitude = round(
            zone.center_lon + random.uniform(-zone.spread, zone.spread),
            6,
        )

        customers.append(
            {
                "customer_id": f"CUS-{i:06d}",
                "zone_id": zone.zone_id,
                "latitude": latitude,
                "longitude": longitude,
            }
        )

    return customers


def save_customers(customers: list[dict]) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "customers.csv"

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "customer_id",
                "zone_id",
                "latitude",
                "longitude",
            ],
        )

        writer.writeheader()
        writer.writerows(customers)

    print(f"Generated {len(customers)} customers")
    print(f"Dataset saved to: {output_file}")


if __name__ == "__main__":
    customers = generate_customers(100)
    save_customers(customers)