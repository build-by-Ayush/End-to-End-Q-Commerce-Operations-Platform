from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from simulator.geography import BENGALURU_ZONES


def generate_stores(count: int = 20) -> list[dict]:
    stores = []

    base_open_date = datetime(2025, 1, 1)

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

        opened_at = base_open_date + timedelta(
            days=random.randint(0, 365)
        )

        stores.append(
            {
                "store_id": f"STR-{i:03d}",
                "store_name": f"Dark Store {i:03d}",
                "zone": zone.zone_id,
                "latitude": latitude,
                "longitude": longitude,
                "baseline_capacity": random.randint(80, 180),
                "status": "ACTIVE",
                "opened_at": opened_at.strftime("%Y-%m-%d %H:%M:%S"),
                "closed_at": "",
            }
        )

    return stores


def save_stores(stores: list[dict]) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "stores.csv"

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
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

        writer.writeheader()
        writer.writerows(stores)

    print(f"Generated {len(stores)} stores")
    print(f"Dataset saved to: {output_file}")


if __name__ == "__main__":
    stores = generate_stores(20)
    save_stores(stores)