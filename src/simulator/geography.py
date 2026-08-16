from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    zone_id: str
    center_lat: float
    center_lon: float
    spread: float


BENGALURU_ZONES = [
    Zone("BLR-CEN", 12.9716, 77.5946, 0.025),
    Zone("BLR-NTH", 13.0500, 77.5900, 0.035),
    Zone("BLR-STH", 12.9000, 77.5900, 0.035),
    Zone("BLR-EST", 12.9700, 77.6700, 0.035),
    Zone("BLR-WST", 12.9600, 77.5300, 0.035),
]