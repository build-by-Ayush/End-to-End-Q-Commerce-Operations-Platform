from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from simulator.geography import BENGALURU_ZONES


VEHICLE_TYPES = [
    "BIKE",
    "SCOOTER",
]


def generate_riders(count: int = 50) -> list[dict]:
    riders = []

    base_join_date = datetime(2025, 1, 1)

    for i in range(1, count + 1):
        zone = random.choice(BENGALURU_ZONES)

        joined_at = base_join_date + timedelta(
            days=random.randint(0, 365)
        )

        riders.append(
            {
                "rider_id": f"RID-{i:06d}",
                "vehicle_type": random.choice(VEHICLE_TYPES),
                "home_zone": zone.zone_id,
                "status": "ACTIVE",
                "joined_at": joined_at.strftime("%Y-%m-%d %H:%M:%S"),
                "deactivated_at": "",
            }
        )

    return riders


def save_riders(riders: list[dict]) -> None:
    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "riders.csv"

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "rider_id",
                "vehicle_type",
                "home_zone",
                "status",
                "joined_at",
                "deactivated_at",
            ],
        )

        writer.writeheader()
        writer.writerows(riders)

    print(f"Generated {len(riders)} riders")
    print(f"Dataset saved to: {output_file}")


if __name__ == "__main__":
    riders = generate_riders(50)
    save_riders(riders)