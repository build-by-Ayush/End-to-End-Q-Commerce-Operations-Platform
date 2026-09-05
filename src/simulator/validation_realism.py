"""
Second-layer Q-Commerce dataset audit.

Run from project root:
    python src/simulator/validation_realism.py
or:
    python src/simulator/validation_realism.py src/datasets

This validates GENERATED CSV data, not Python syntax/style.
It focuses on logical integrity, lifecycle consistency, resource realism,
30-day calendar coverage, and dashboard-impacting anomalies.
"""
from __future__ import annotations

import csv
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[1] / "datasets"
EXPECTED_FILES = [
    "customers.csv", "stores.csv", "riders.csv", "orders.csv",
    "fulfilment_units.csv", "order_items.csv", "deliveries.csv",
    "rider_assignments.csv", "operational_events.csv", "store_staffing.csv",
]

TARGET_DAYS = 30
SLA_TARGET = 20
SLA_GRACE = 5

# Broad sanity bounds, deliberately conservative. These are not claims about
# any proprietary quick-commerce operator.
MAX_FU_PER_ORDER = 3
MAX_ITEMS_PER_ORDER = 20
MAX_DISTANCE_KM = 30
MAX_STORE_SHARE = 0.20
MAX_DAY_SHARE = 0.10
MAX_HOUR_SHARE = 0.15
MAX_ORDERS_ONE_CUSTOMER = 50

EVENT_STAGE = {
    "STORE_ASSIGNED": 1,
    "PICKING_STARTED": 2,
    "PICKING_COMPLETED": 3,
    "PACKING_STARTED": 4,
    "PACKING_COMPLETED": 5,
    "RIDER_ASSIGNED": 6,
    "RIDER_ARRIVED_AT_STORE": 7,
    "PICKED_UP": 8,
    "DELIVERY_STARTED": 9,
    "DELIVERED": 10,
    "DELIVERY_FAILED": 10,
    "FULFILMENT_FAILED": 10,
    "FULFILMENT_CANCELLED": 10,
}

class Result:
    def __init__(self) -> None:
        self.critical: list[str] = []
        self.major: list[str] = []
        self.minor: list[str] = []
        self.metrics: dict[str, object] = {}

    def add(self, severity: str, message: str) -> None:
        getattr(self, severity.lower()).append(message)

    def report(self) -> None:
        print("\n" + "=" * 72)
        print("Q-COMMERCE SECOND-LAYER LOGIC + REALISM AUDIT")
        print("=" * 72)
        print("\nSUMMARY")
        print(f"  CRITICAL : {len(self.critical)}")
        print(f"  MAJOR    : {len(self.major)}")
        print(f"  MINOR    : {len(self.minor)}")
        if self.critical:
            verdict = "SIGNIFICANT LOGICAL ISSUES"
        elif self.major:
            verdict = "GENERALLY SOUND WITH MAJOR ISSUES"
        elif self.minor:
            verdict = "LOGICALLY SOUND WITH MINOR REALISM NOTES"
        else:
            verdict = "LOGICALLY SOUND"
        print(f"\nOVERALL VERDICT: {verdict}")

        if self.metrics:
            print("\nKEY METRICS")
            for k, v in self.metrics.items():
                print(f"  {k}: {v}")

        for name, values in (
            ("CRITICAL", self.critical),
            ("MAJOR", self.major),
            ("MINOR", self.minor),
        ):
            if values:
                print(f"\n{name}")
                for message in values:
                    print(f"  [{name}] {message}")
        print("\n" + "=" * 72)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ts(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def num(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    n = len(values)
    m = n // 2
    return values[m] if n % 2 else (values[m - 1] + values[m]) / 2


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    rank = (len(values) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (rank - lo)


def pct(a: int, b: int) -> str:
    return f"{(a / b * 100 if b else 0):.1f}%"


def load(dataset_dir: Path) -> dict[str, list[dict[str, str]]]:
    data: dict[str, list[dict[str, str]]] = {}
    print(f"\nReading: {dataset_dir}")
    for file_name in EXPECTED_FILES:
        rows = read_csv(dataset_dir / file_name)
        data[Path(file_name).stem] = rows
        print(f"  {file_name:28s} {len(rows):>12,}")
    return data


def check_ids_and_fks(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    pk = {
        "customers": "customer_id", "stores": "store_id", "riders": "rider_id",
        "orders": "order_id", "fulfilment_units": "fulfilment_unit_id",
        "order_items": "order_item_id", "deliveries": "delivery_id",
        "rider_assignments": "assignment_id", "operational_events": "event_id",
        "store_staffing": "staffing_snapshot_id",
    }
    ids: dict[str, set[str]] = {}
    for table, key in pk.items():
        vals = [row.get(key, "") for row in data[table]]
        miss = sum(not x for x in vals)
        dup = len(vals) - len(set(vals))
        if miss:
            r.add("CRITICAL", f"{table}: {miss:,} rows have missing {key}.")
        if dup:
            r.add("CRITICAL", f"{table}: {dup:,} duplicate {key} values.")
        ids[table] = set(x for x in vals if x)

    fks = [
        ("orders", "customer_id", "customers"),
        ("fulfilment_units", "order_id", "orders"),
        ("fulfilment_units", "store_id", "stores"),
        ("order_items", "order_id", "orders"),
        ("order_items", "fulfilment_unit_id", "fulfilment_units"),
        ("deliveries", "fulfilment_unit_id", "fulfilment_units"),
        ("deliveries", "rider_id", "riders"),
        ("rider_assignments", "delivery_id", "deliveries"),
        ("rider_assignments", "rider_id", "riders"),
        ("operational_events", "order_id", "orders"),
        ("operational_events", "fulfilment_unit_id", "fulfilment_units"),
        ("operational_events", "delivery_id", "deliveries"),
        ("operational_events", "store_id", "stores"),
        ("operational_events", "rider_id", "riders"),
        ("store_staffing", "store_id", "stores"),
    ]
    for table, fk, parent in fks:
        broken = sum(
            bool(row.get(fk)) and row[fk] not in ids[parent]
            for row in data[table]
        )
        if broken:
            r.add("CRITICAL", f"{table}: {broken:,} broken {fk} references to {parent}.")


def check_calendar(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    order_times = [x for x in (ts(row.get("created_at")) for row in data["orders"]) if x]
    staff_times = [x for x in (ts(row.get("recorded_at")) for row in data["store_staffing"]) if x]
    if not order_times:
        r.add("CRITICAL", "orders: no valid created_at timestamps.")
        return
    start, end = min(order_times), max(order_times)
    day_span = (end.date() - start.date()).days + 1
    r.metrics["Order calendar span"] = f"{day_span} days ({start.date()} -> {end.date()})"
    if day_span < TARGET_DAYS:
        r.add("MAJOR", f"Orders span {day_span} calendar days; target is {TARGET_DAYS}.")

    stores = {row.get("store_id") for row in data["stores"]}
    if not staff_times:
        r.add("CRITICAL", "store_staffing: no valid recorded_at timestamps.")
        return
    smin, smax = min(staff_times), max(staff_times)
    staff_days = (smax.date() - smin.date()).days + 1
    expected = len(stores) * TARGET_DAYS * 24
    r.metrics["Staffing calendar span"] = f"{staff_days} days ({smin.date()} -> {smax.date()})"
    r.metrics["Expected hourly staffing rows"] = expected
    if len(data["store_staffing"]) != expected:
        r.add(
            "MAJOR",
            f"store_staffing has {len(data['store_staffing']):,} rows; expected "
            f"{expected:,} for {len(stores)} stores × {TARGET_DAYS} days × 24 hours.",
        )
    staff_stores = {row.get("store_id") for row in data["store_staffing"]}
    if staff_stores != stores:
        r.add("CRITICAL", "store_staffing store coverage differs from stores.")


def check_cardinality(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    orders = data["orders"]
    fus = data["fulfilment_units"]
    items = data["order_items"]
    deliveries = data["deliveries"]
    fus_by_order = Counter(x.get("order_id", "") for x in fus)
    item_by_order = Counter(x.get("order_id", "") for x in items)
    delivery_by_fu = Counter(x.get("fulfilment_unit_id", "") for x in deliveries)

    missing_fu = sum(fus_by_order[o["order_id"]] == 0 for o in orders)
    missing_items = sum(item_by_order[o["order_id"]] == 0 for o in orders)
    bad_delivery_count = sum(delivery_by_fu[fu["fulfilment_unit_id"]] != 1 for fu in fus)
    if missing_fu:
        r.add("CRITICAL", f"{missing_fu:,} orders have no fulfilment unit.")
    if missing_items:
        r.add("MAJOR", f"{missing_items:,} orders have no order-item rows.")
    if bad_delivery_count:
        r.add("CRITICAL", f"{bad_delivery_count:,} fulfilment units do not have exactly one delivery.")

    avg_fu = len(fus) / len(orders) if orders else 0
    avg_items = len(items) / len(orders) if orders else 0
    r.metrics["Fulfilments / order"] = round(avg_fu, 3)
    r.metrics["Item rows / order"] = round(avg_items, 3)
    r.metrics["Deliveries / fulfilment"] = round(len(deliveries) / len(fus), 3) if fus else 0
    if avg_fu > MAX_FU_PER_ORDER:
        r.add("MINOR", f"Average fulfilments/order is {avg_fu:.2f}; unusually high for the simplified model.")
    if avg_items < 1:
        r.add("MAJOR", "Average order-item rows/order is below 1.")

    bad_qty = 0
    for row in items:
        try:
            q = int(row.get("quantity", ""))
            if q <= 0:
                bad_qty += 1
        except ValueError:
            bad_qty += 1
    if bad_qty:
        r.add("CRITICAL", f"{bad_qty:,} order-item rows have invalid/non-positive quantity.")


def check_demand(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    orders = data["orders"]
    by_day, by_hour, by_customer, by_store = Counter(), Counter(), Counter(), Counter()
    for row in orders:
        t = ts(row.get("created_at"))
        if t:
            by_day[t.date()] += 1
            by_hour[t.hour] += 1
        by_customer[row.get("customer_id", "")] += 1
    for row in data["fulfilment_units"]:
        by_store[row.get("store_id", "")] += 1

    total = len(orders)
    if total and by_day:
        day, n = by_day.most_common(1)[0]
        share = n / total
        r.metrics["Busiest day share"] = f"{share:.2%} ({day})"
        if share > MAX_DAY_SHARE:
            r.add("MAJOR", f"Busiest day contains {share:.1%} of all orders; this suggests artificial concentration.")
    if total and by_hour:
        hour, n = by_hour.most_common(1)[0]
        share = n / total
        r.metrics["Busiest hour share"] = f"{share:.2%} ({hour:02d}:00)"
        if share > MAX_HOUR_SHARE:
            r.add("MAJOR", f"Hour {hour:02d}:00 contains {share:.1%} of all orders; inspect the earlier late-hour concentration problem.")
    if by_store and data["fulfilment_units"]:
        store, n = by_store.most_common(1)[0]
        share = n / len(data["fulfilment_units"])
        r.metrics["Largest store fulfilment share"] = f"{share:.2%} ({store})"
        if share > MAX_STORE_SHARE:
            r.add("MAJOR", f"Store {store} handles {share:.1%} of fulfilments; inspect store allocation logic.")
    counts = list(by_customer.values())
    if counts:
        r.metrics["Ordering customers"] = len(counts)
        r.metrics["Average orders / ordering customer"] = round(sum(counts) / len(counts), 3)
        r.metrics["Max orders by one customer"] = max(counts)
        if max(counts) > MAX_ORDERS_ONE_CUSTOMER:
            r.add("MINOR", f"One customer has {max(counts)} orders in 30 days; unusually high for this synthetic population.")


def check_assignments(data: dict[str, list[dict[str, str]]], r: Result) -> dict[str, set[str]]:
    accepted: dict[str, set[str]] = defaultdict(set)
    for row in data["rider_assignments"]:
        aid = row.get("assignment_id", "")
        response = row.get("response", "")
        offered, responded, expired = ts(row.get("offered_at")), ts(row.get("responded_at")), ts(row.get("expired_at"))
        delivery_id, rider_id = row.get("delivery_id", ""), row.get("rider_id", "")
        if response == "ACCEPTED":
            accepted[delivery_id].add(rider_id)
            if not responded or expired:
                r.add("CRITICAL", f"Accepted assignment {aid} has invalid response timestamps.")
        elif response == "REJECTED":
            if not responded or expired or not row.get("rejection_reason"):
                r.add("CRITICAL", f"Rejected assignment {aid} has invalid responded/expired/rejection fields.")
        elif response == "EXPIRED":
            # This is the exact defect seen in the earlier audit.
            if responded:
                r.add("CRITICAL", f"Expired assignment {aid} has responded_at populated; expired offers should have responded_at NULL.")
            if not expired:
                r.add("CRITICAL", f"Expired assignment {aid} has no expired_at.")
            if row.get("rejection_reason"):
                r.add("MINOR", f"Expired assignment {aid} has a rejection_reason.")
        else:
            r.add("CRITICAL", f"Assignment {aid} has unsupported response={response!r}.")
        terminal = responded or expired
        if offered and terminal and terminal < offered:
            r.add("CRITICAL", f"Assignment {aid} terminates before offered_at.")
    multi = {d: riders for d, riders in accepted.items() if len(riders) > 1}
    if multi:
        r.add("CRITICAL", f"{len(multi):,} deliveries have more than one accepted rider.")
    r.metrics["Assignment attempts"] = len(data["rider_assignments"])
    r.metrics["Accepted deliveries"] = sum(bool(x) for x in accepted.values())
    return accepted


def check_events(data: dict[str, list[dict[str, str]]], accepted: dict[str, set[str]], r: Result) -> None:
    orders = {x["order_id"] for x in data["orders"]}
    fus = {x["fulfilment_unit_id"] for x in data["fulfilment_units"]}
    deliveries = {x["delivery_id"] for x in data["deliveries"]}
    event_types: dict[str, set[str]] = defaultdict(set)
    rider_assigned: dict[str, set[str]] = defaultdict(set)
    last_time: dict[str, datetime] = {}
    last_stage: dict[str, int] = {}

    for e in data["operational_events"]:
        eid = e.get("event_id", "")
        oid, fid, did, rid = e.get("order_id", ""), e.get("fulfilment_unit_id", ""), e.get("delivery_id", ""), e.get("rider_id", "")
        if oid and oid not in orders:
            r.add("CRITICAL", f"Event {eid} references nonexistent order {oid}.")
        if fid and fid not in fus:
            r.add("CRITICAL", f"Event {eid} references nonexistent fulfilment {fid}.")
        if did and did not in deliveries:
            r.add("CRITICAL", f"Event {eid} references nonexistent delivery {did}.")
        t = ts(e.get("occurred_at"))
        if not t:
            r.add("CRITICAL", f"Event {eid} has invalid occurred_at.")
            continue
        if did:
            event_types[did].add(e.get("event_type", ""))
            if did in last_time and t < last_time[did]:
                r.add("CRITICAL", f"Delivery {did} has backwards event time.")
            last_time[did] = t
            stage = EVENT_STAGE.get(e.get("event_type", ""))
            if stage is not None:
                previous = last_stage.get(did)
                if previous is not None and stage < previous:
                    r.add("CRITICAL", f"Delivery {did} has impossible lifecycle order around {e.get('event_type') }.")
                last_stage[did] = max(previous or stage, stage)
        if e.get("event_type") == "RIDER_ASSIGNED":
            rider_assigned[did].add(rid)

    # Known synchronization failure from the previous version.
    for did, accepted_riders in accepted.items():
        if rider_assigned.get(did, set()) != accepted_riders:
            r.add("CRITICAL", f"Delivery {did}: accepted rider(s) {sorted(accepted_riders)} do not exactly match RIDER_ASSIGNED event rider(s) {sorted(rider_assigned.get(did, set()))}.")

    for delivery in data["deliveries"]:
        did, status = delivery["delivery_id"], delivery.get("status", "")
        ev = event_types.get(did, set())
        if status == "DELIVERED":
            required = {"RIDER_ASSIGNED", "RIDER_ARRIVED_AT_STORE", "PICKED_UP", "DELIVERY_STARTED", "DELIVERED"}
            missing = required - ev
            if missing:
                r.add("CRITICAL", f"Delivered delivery {did} is missing events {sorted(missing)}.")
        elif status == "FAILED" and not ({"DELIVERY_FAILED", "FULFILMENT_FAILED"} & ev):
            r.add("CRITICAL", f"Failed delivery {did} has no failure event.")
        elif status == "CANCELLED" and "FULFILMENT_CANCELLED" not in ev:
            r.add("MAJOR", f"Cancelled delivery {did} has no FULFILMENT_CANCELLED event.")

    r.metrics["Operational events"] = len(data["operational_events"])
    r.metrics["Events / delivery"] = round(len(data["operational_events"]) / len(deliveries), 3) if deliveries else 0


def check_states(data: dict[str, list[dict[str, str]]], accepted: dict[str, set[str]], r: Result) -> None:
    fus = {x["fulfilment_unit_id"]: x for x in data["fulfilment_units"]}
    deliveries = {x["delivery_id"]: x for x in data["deliveries"]}
    for d in deliveries.values():
        f = fus.get(d.get("fulfilment_unit_id", ""))
        if not f:
            continue
        expected = {"DELIVERED": "COMPLETED", "FAILED": "FAILED", "CANCELLED": "CANCELLED"}.get(d.get("status"))
        if expected and f.get("status") != expected:
            r.add("CRITICAL", f"Delivery {d['delivery_id']} is {d.get('status')} but fulfilment is {f.get('status')}.")
        status = d.get("status", "")
        fields = ["rider_id", "rider_arrived_at_store", "picked_up_at", "delivery_started_at", "delivered_at"]
        if status == "DELIVERED":
            missing = [x for x in fields if not d.get(x)]
            if missing:
                r.add("CRITICAL", f"Delivered delivery {d['delivery_id']} is missing fields {missing}.")
        if status in {"FAILED", "CANCELLED"} and d.get("delivered_at"):
            r.add("CRITICAL", f"Terminal delivery {d['delivery_id']} is {status} but has delivered_at.")
        if status == "REQUESTED" and d.get("rider_id"):
            r.add("MAJOR", f"Requested delivery {d['delivery_id']} already has rider_id={d['rider_id']}.")

    # Delivery rider must match accepted assignment.
    mismatch = 0
    for did, riders in accepted.items():
        d = deliveries.get(did)
        if d and d.get("rider_id") and d["rider_id"] not in riders:
            mismatch += 1
    if mismatch:
        r.add("CRITICAL", f"{mismatch:,} deliveries have final rider_id different from accepted assignment rider.")


def check_time_causality(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    orders = {x["order_id"]: x for x in data["orders"]}
    for o in data["orders"]:
        a, b = ts(o.get("created_at")), ts(o.get("payment_success_at"))
        if a and b and b < a:
            r.add("CRITICAL", f"Order {o['order_id']} has payment before creation.")
    for fu in data["fulfilment_units"]:
        pairs = [
            ("assigned_to_store_at", "picking_started_at"),
            ("picking_started_at", "picking_completed_at"),
            ("picking_completed_at", "packing_started_at"),
            ("packing_started_at", "packing_completed_at"),
        ]
        for left, right in pairs:
            a, b = ts(fu.get(left)), ts(fu.get(right))
            if a and b and b < a:
                r.add("CRITICAL", f"Fulfilment {fu['fulfilment_unit_id']} has {right} before {left}.")
        order = orders.get(fu.get("order_id", ""))
        payment = ts(order.get("payment_success_at")) if order else None
        assigned = ts(fu.get("assigned_to_store_at"))
        if payment and assigned and assigned < payment:
            r.add("CRITICAL", f"Fulfilment {fu['fulfilment_unit_id']} is assigned before payment succeeds.")

    for d in data["deliveries"]:
        pairs = [
            ("rider_arrived_at_store", "picked_up_at"),
            ("picked_up_at", "delivery_started_at"),
            ("delivery_started_at", "delivered_at"),
        ]
        for left, right in pairs:
            a, b = ts(d.get(left)), ts(d.get(right))
            if a and b and b < a:
                r.add("CRITICAL", f"Delivery {d['delivery_id']} has {right} before {left}.")


def check_order_rollup(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    by_order: dict[str, list[str]] = defaultdict(list)
    for fu in data["fulfilment_units"]:
        by_order[fu["order_id"]].append(fu.get("status", ""))
    for order in data["orders"]:
        statuses = by_order.get(order["order_id"], [])
        if not statuses or any(s not in {"COMPLETED", "FAILED", "CANCELLED"} for s in statuses):
            continue
        status = order.get("status", "")
        failed = statuses.count("FAILED")
        cancelled = statuses.count("CANCELLED")
        completed = statuses.count("COMPLETED")
        # Existing business rule: any failed fulfilment => parent FAILED.
        if failed and status != "FAILED":
            r.add("CRITICAL", f"Order {order['order_id']} has failed fulfilment(s) but status={status!r}.")
        elif not failed and not cancelled and completed == len(statuses) and status != "DELIVERED":
            r.add("CRITICAL", f"Order {order['order_id']} has all fulfilments COMPLETED but status={status!r}.")
        elif not failed and cancelled == len(statuses) and status != "CANCELLED":
            r.add("CRITICAL", f"Order {order['order_id']} has all fulfilments CANCELLED but status={status!r}.")


def check_rider_concurrency(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    by_rider: dict[str, list[tuple[datetime, datetime, str]]] = defaultdict(list)
    for d in data["deliveries"]:
        rider = d.get("rider_id", "")
        if d.get("status") != "DELIVERED" or not rider:
            continue
        start = ts(d.get("rider_arrived_at_store")) or ts(d.get("picked_up_at")) or ts(d.get("delivery_started_at"))
        end = ts(d.get("delivered_at"))
        if start and end and end >= start:
            by_rider[rider].append((start, end, d["delivery_id"]))
    overlaps = 0
    max_active = 0
    for rider, trips in by_rider.items():
        trips.sort(key=lambda x: x[0])
        active: list[tuple[datetime, datetime, str]] = []
        for start, end, did in trips:
            active = [x for x in active if x[1] > start]
            overlaps += len(active)
            max_active = max(max_active, len(active) + 1 if active else 1)
            active.append((start, end, did))
    r.metrics["Rider overlapping-delivery pairs"] = overlaps
    r.metrics["Max concurrent deliveries for one rider"] = max_active
    if overlaps:
        r.add("CRITICAL", f"{overlaps:,} rider delivery overlaps detected. A rider is concurrently handling more than one delivery.")


def check_staffing(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    rows = data["store_staffing"]
    keys = Counter((x.get("store_id", ""), x.get("recorded_at", "")) for x in rows)
    dup = sum(n - 1 for n in keys.values() if n > 1)
    if dup:
        r.add("CRITICAL", f"{dup:,} duplicate store/hour staffing snapshots.")
    picker_equal = packer_equal = invalid = 0
    for x in rows:
        try:
            ps, pa = int(x.get("pickers_scheduled", "")), int(x.get("pickers_available", ""))
            ks, ka = int(x.get("packers_scheduled", "")), int(x.get("packers_available", ""))
        except ValueError:
            invalid += 1
            continue
        if min(ps, pa, ks, ka) < 0 or pa > ps or ka > ks:
            invalid += 1
        picker_equal += pa == ps
        packer_equal += ka == ks
    if invalid:
        r.add("CRITICAL", f"{invalid:,} staffing rows have negative/invalid counts or available > scheduled.")
    if rows:
        p1, p2 = picker_equal / len(rows), packer_equal / len(rows)
        r.metrics["Picker scheduled=available"] = f"{p1:.1%}"
        r.metrics["Packer scheduled=available"] = f"{p2:.1%}"
        if p1 >= 0.95:
            r.add("MINOR", f"{p1:.1%} of staffing snapshots have pickers_scheduled == pickers_available; staffing may be too clean.")
        if p2 >= 0.95:
            r.add("MINOR", f"{p2:.1%} of staffing snapshots have packers_scheduled == packers_available; staffing may be too clean.")


def check_delivery_realism(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    distances, transits = [], []
    traffic, weather, status = Counter(), Counter(), Counter()
    for d in data["deliveries"]:
        status[d.get("status", "")] += 1
        x = num(d.get("delivery_distance"))
        if x is not None:
            distances.append(x)
        if d.get("traffic_condition"):
            traffic[d["traffic_condition"]] += 1
        if d.get("weather_condition"):
            weather[d["weather_condition"]] += 1
        start = ts(d.get("delivery_started_at")) or ts(d.get("picked_up_at"))
        end = ts(d.get("delivered_at"))
        if start and end and end >= start:
            transits.append((end - start).total_seconds() / 60)
    if distances:
        r.metrics["Delivery distance median"] = f"{median(distances):.2f} km"
        r.metrics["Delivery distance p95"] = f"{percentile(distances, .95):.2f} km"
        too_far = sum(x > MAX_DISTANCE_KM for x in distances)
        nonpositive = sum(x <= 0 for x in distances)
        if too_far:
            r.add("MAJOR", f"{too_far:,} delivery distances exceed {MAX_DISTANCE_KM} km.")
        if nonpositive:
            r.add("CRITICAL", f"{nonpositive:,} deliveries have non-positive distance.")
    if transits:
        r.metrics["Transit median"] = f"{median(transits):.2f} min"
        r.metrics["Transit p95"] = f"{percentile(transits, .95):.2f} min"
        if any(x <= 0 for x in transits):
            r.add("CRITICAL", "At least one delivered trip has non-positive transit duration.")
    r.metrics["Traffic categories"] = dict(traffic)
    r.metrics["Weather categories"] = dict(weather)
    r.metrics["Delivery statuses"] = dict(status)
    if len(traffic) <= 1:
        r.add("MINOR", "Traffic has only one category; segmentation will have little analytical value.")
    if len(weather) <= 1:
        r.add("MINOR", "Weather has only one category; weather impact cannot be meaningfully segmented.")


def check_sla(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    orders = {x["order_id"]: x for x in data["orders"]}
    deliveries = {x["fulfilment_unit_id"]: x for x in data["deliveries"]}
    durations, target = [], [0, 0, 0]
    for fu in data["fulfilment_units"]:
        d = deliveries.get(fu["fulfilment_unit_id"])
        o = orders.get(fu.get("order_id", ""))
        if not d or not o or d.get("status") != "DELIVERED":
            continue
        p, end = ts(o.get("payment_success_at")), ts(d.get("delivered_at"))
        if not p or not end:
            r.add("CRITICAL", f"Delivered delivery {d['delivery_id']} cannot produce payment-success-to-delivery SLA duration.")
            continue
        if end < p:
            r.add("CRITICAL", f"Delivery {d['delivery_id']} completes before payment_success_at.")
            continue
        minutes = (end - p).total_seconds() / 60
        durations.append(minutes)
        if minutes <= SLA_TARGET:
            target[0] += 1
        elif minutes <= SLA_TARGET + SLA_GRACE:
            target[1] += 1
        else:
            target[2] += 1
    total = sum(target)
    r.metrics["SLA on target"] = pct(target[0], total)
    r.metrics["SLA within grace"] = pct(target[1], total)
    r.metrics["SLA breach"] = pct(target[2], total)
    if durations:
        r.metrics["SLA median"] = f"{median(durations):.2f} min"
        r.metrics["SLA p95"] = f"{percentile(durations, .95):.2f} min"
    if total and target[2] / total >= .50:
        r.add("MAJOR", f"{target[2] / total:.1%} of delivered operations breach the {SLA_TARGET + SLA_GRACE}-minute threshold. Review the business story; this is a realism concern, not automatically a bug.")


def check_obvious_values(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    for x in data["stores"]:
        cap = num(x.get("baseline_capacity"))
        if cap is None or cap <= 0:
            r.add("CRITICAL", f"Store {x.get('store_id')} has invalid baseline_capacity.")
        if x.get("status") == "ACTIVE" and x.get("closed_at"):
            r.add("MAJOR", f"Store {x.get('store_id')} is ACTIVE but has closed_at.")
    for x in data["riders"]:
        if x.get("status") == "ACTIVE" and x.get("deactivated_at"):
            r.add("MAJOR", f"Rider {x.get('rider_id')} is ACTIVE but has deactivated_at.")


def audit(dataset_dir: Path) -> Result:
    data = load(dataset_dir)
    r = Result()
    check_ids_and_fks(data, r)
    check_calendar(data, r)
    check_cardinality(data, r)
    check_demand(data, r)
    accepted = check_assignments(data, r)
    check_events(data, accepted, r)
    check_states(data, accepted, r)
    check_time_causality(data, r)
    check_order_rollup(data, r)
    check_rider_concurrency(data, r)
    check_staffing(data, r)
    check_delivery_realism(data, r)
    check_sla(data, r)
    check_obvious_values(data, r)
    return r


def main() -> int:
    dataset_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DATASET_DIR.resolve()
    try:
        result = audit(dataset_dir)
    except Exception as exc:
        print("\nAUDIT COULD NOT COMPLETE")
        print(f"Reason: {exc}")
        return 2
    result.report()
    return 1 if result.critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
