"""
Q-Commerce second-layer dataset audit.

This is an independent audit of the GENERATED CSV datasets.
It does not review Python syntax, style, optimization, normalization, etc.

Run from project root:
    python src/simulator/validation_realism.py
or:
    python src/simulator/validation_realism.py src/datasets

The audit follows the project's actual V1 rules:
- 10 raw tables; no product master table
- 30-day simulation
- 1 fulfilment unit normally -> exactly 1 delivery
- split orders are allowed
- parent order roll-up follows the current simulator rule:
      all COMPLETED             -> DELIVERED
      otherwise any CANCELLED   -> CANCELLED
      otherwise any FAILED      -> FAILED
      otherwise                  -> FULFILLING
- cancellation is a fulfilment-level event; it does NOT require delivery_id
- one rider may handle only one active delivery at a time
- SLA clock starts at PAYMENT_SUCCESS
- target 20 min; grace to 25 min; >25 = breach
- customer master location and order delivery location are intentionally
  separate concepts
- staffing is hourly store-level snapshot data

The output is intentionally compact so the beginning of the report is never
lost in a large VS Code terminal dump.
"""
from __future__ import annotations

import csv
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[1] / "datasets"
TARGET_DAYS = 30
SLA_TARGET = 20
SLA_GRACE = 5
MAX_FU_PER_ORDER = 3
MAX_ITEMS_PER_ORDER = 20
MAX_DISTANCE_KM = 30
MAX_STORE_SHARE = 0.20
MAX_DAY_SHARE = 0.10
MAX_HOUR_SHARE = 0.15
MAX_ORDERS_ONE_CUSTOMER = 50
MAX_EXAMPLES_PER_ISSUE = 5

EXPECTED_COLUMNS = {
    "customers": ["customer_id", "zone_id", "latitude", "longitude"],
    "stores": ["store_id", "store_name", "zone", "latitude", "longitude", "baseline_capacity", "status", "opened_at", "closed_at"],
    "riders": ["rider_id", "vehicle_type", "home_zone", "status", "joined_at", "deactivated_at"],
    "orders": ["order_id", "customer_id", "created_at", "payment_success_at", "delivery_latitude", "delivery_longitude", "delivery_zone", "status", "cancelled_at", "cancellation_reason", "failure_reason"],
    "fulfilment_units": ["fulfilment_unit_id", "order_id", "store_id", "status", "assigned_to_store_at", "picking_started_at", "picking_completed_at", "packing_started_at", "packing_completed_at", "cancelled_at", "cancellation_reason", "failed_at", "failure_reason", "completed_at"],
    "order_items": ["order_item_id", "order_id", "fulfilment_unit_id", "product_id", "quantity"],
    "deliveries": ["delivery_id", "fulfilment_unit_id", "rider_id", "status", "rider_arrived_at_store", "picked_up_at", "delivery_started_at", "delivered_at", "delivery_distance", "traffic_condition", "weather_condition", "cancelled_at", "cancellation_reason", "failed_at", "failure_reason"],
    "rider_assignments": ["assignment_id", "delivery_id", "rider_id", "offered_at", "responded_at", "expired_at", "response", "rejection_reason"],
    "operational_events": ["event_id", "event_type", "occurred_at", "order_id", "fulfilment_unit_id", "delivery_id", "store_id", "rider_id", "reason"],
    "store_staffing": ["staffing_snapshot_id", "store_id", "recorded_at", "pickers_scheduled", "pickers_available", "packers_scheduled", "packers_available"],
}

EXPECTED_FILES = [f"{name}.csv" for name in EXPECTED_COLUMNS]

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

TERMINAL_FU = {"COMPLETED", "FAILED", "CANCELLED"}


class Result:
    def __init__(self) -> None:
        self.critical: list[tuple[str, str]] = []
        self.major: list[tuple[str, str]] = []
        self.minor: list[tuple[str, str]] = []
        self.metrics: dict[str, object] = {}
        self.counts: Counter[str] = Counter()

    def add(self, severity: str, message: str) -> None:
        severity = severity.upper()
        self.counts[message] += 1
        bucket = getattr(self, severity.lower())
        # Store only a few examples for each exact issue text.
        existing = sum(1 for m, _ in bucket if m == message)
        if existing < MAX_EXAMPLES_PER_ISSUE:
            bucket.append((message, message))

    def unique_issues(self, bucket: list[tuple[str, str]]) -> list[tuple[str, int]]:
        counts = Counter(message for message, _ in bucket)
        return list(counts.items())

    def report(self, dataset_dir: Path) -> None:
        print("\n" + "=" * 72)
        print("Q-COMMERCE SECOND-LAYER LOGIC + REALISM AUDIT")
        print("=" * 72)
        print(f"Dataset: {dataset_dir}")

        print("\nVERDICT")
        print("-" * 72)
        if self.critical:
            verdict = "SIGNIFICANT LOGICAL ISSUES"
        elif self.major:
            verdict = "GENERALLY SOUND WITH MAJOR ISSUES"
        elif self.minor:
            verdict = "LOGICALLY SOUND WITH MINOR REALISM NOTES"
        else:
            verdict = "LOGICALLY SOUND"
        print(verdict)

        print("\nISSUE COUNTS")
        print("-" * 72)
        print(f"CRITICAL : {len(self.critical)}")
        print(f"MAJOR    : {len(self.major)}")
        print(f"MINOR    : {len(self.minor)}")

        if self.metrics:
            print("\nKEY METRICS")
            print("-" * 72)
            for key, value in self.metrics.items():
                print(f"{key}: {value}")

        self._print_bucket("CRITICAL", self.critical)
        self._print_bucket("MAJOR", self.major)
        self._print_bucket("MINOR", self.minor)

        print("\n" + "=" * 72)

    @staticmethod
    def _print_bucket(name: str, bucket: list[tuple[str, str]]) -> None:
        if not bucket:
            return
        grouped: list[tuple[str, int]] = []
        seen: set[str] = set()
        all_messages = [message for message, _ in bucket]
        for message in all_messages:
            if message in seen:
                continue
            seen.add(message)
            grouped.append((message, all_messages.count(message)))

        print(f"\n{name}")
        print("-" * 72)
        for message, count in grouped:
            suffix = f" (examples shown: {count})" if count > 1 else ""
            print(f"[{name}] {message}{suffix}")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    # Simulator uses ISO timestamps; support the pasted dd-mm-yyyy format too.
    for parser in (
        datetime.fromisoformat,
        lambda x: datetime.strptime(x, "%d-%m-%Y %H:%M"),
    ):
        try:
            return parser(value)
        except ValueError:
            pass
    raise ValueError(f"Invalid timestamp: {value}")


def num(value: str | None) -> float | None:
    if value is None or value == "":
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
    lo, hi = math.floor(rank), math.ceil(rank)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (rank - lo)


def pct(a: int, b: int) -> str:
    return f"{(a / b * 100 if b else 0):.1f}%"


def load(dataset_dir: Path, r: Result) -> dict[str, list[dict[str, str]]]:
    data: dict[str, list[dict[str, str]]] = {}
    print(f"\nReading datasets from: {dataset_dir}")
    for file_name in EXPECTED_FILES:
        rows = read_csv(dataset_dir / file_name)
        key = Path(file_name).stem
        data[key] = rows
        print(f"  {file_name:28s} {len(rows):>12,}")
    return data


def check_columns(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    for table, expected in EXPECTED_COLUMNS.items():
        actual = list(data[table][0].keys()) if data[table] else []
        missing = [col for col in expected if col not in actual]
        extra = [col for col in actual if col not in expected]
        if missing:
            r.add("CRITICAL", f"{table}: missing expected columns {missing}.")
        if extra:
            r.add("MAJOR", f"{table}: unexpected columns present {extra}.")


def check_ids_and_fks(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    pk = {
        table: cols[0]
        for table, cols in EXPECTED_COLUMNS.items()
    }
    ids: dict[str, set[str]] = {}
    for table, key in pk.items():
        values = [row.get(key, "") for row in data[table]]
        missing = sum(not x for x in values)
        duplicates = len(values) - len(set(values))
        if missing:
            r.add("CRITICAL", f"{table}: {missing:,} rows have missing {key}.")
        if duplicates:
            r.add("CRITICAL", f"{table}: {duplicates:,} duplicate {key} values.")
        ids[table] = {x for x in values if x}

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
    order_times = [parse_ts(x.get("created_at")) for x in data["orders"]]
    order_times = [x for x in order_times if x]
    staff_times = [parse_ts(x.get("recorded_at")) for x in data["store_staffing"]]
    staff_times = [x for x in staff_times if x]

    if not order_times:
        r.add("CRITICAL", "orders: no valid created_at timestamps.")
        return

    start, end = min(order_times), max(order_times)
    days = (end.date() - start.date()).days + 1
    r.metrics["Order calendar"] = f"{days} days ({start.date()} -> {end.date()})"
    if days != TARGET_DAYS:
        r.add("MAJOR", f"Orders span {days} calendar days; expected {TARGET_DAYS}.")

    stores = {x.get("store_id") for x in data["stores"]}
    if not staff_times:
        r.add("CRITICAL", "store_staffing: no valid recorded_at timestamps.")
        return

    smin, smax = min(staff_times), max(staff_times)
    staff_days = (smax.date() - smin.date()).days + 1
    expected = len(stores) * TARGET_DAYS * 24
    r.metrics["Staffing calendar"] = f"{staff_days} days ({smin.date()} -> {smax.date()})"
    r.metrics["Expected hourly staffing rows"] = expected
    r.metrics["Actual staffing rows"] = len(data["store_staffing"])

    if len(data["store_staffing"]) != expected:
        r.add("MAJOR", f"store_staffing has {len(data['store_staffing']):,} rows; expected {expected:,}.")

    staff_stores = {x.get("store_id") for x in data["store_staffing"]}
    if staff_stores != stores:
        r.add("CRITICAL", "store_staffing store coverage differs from stores.")


def check_cardinality(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    orders, fus, items, deliveries = data["orders"], data["fulfilment_units"], data["order_items"], data["deliveries"]
    fus_by_order = Counter(x.get("order_id", "") for x in fus)
    items_by_order = Counter(x.get("order_id", "") for x in items)
    deliveries_by_fu = Counter(x.get("fulfilment_unit_id", "") for x in deliveries)

    missing_fu = sum(fus_by_order[o["order_id"]] == 0 for o in orders)
    missing_items = sum(items_by_order[o["order_id"]] == 0 for o in orders)
    bad_delivery = sum(deliveries_by_fu[f["fulfilment_unit_id"]] != 1 for f in fus)

    if missing_fu:
        r.add("CRITICAL", f"{missing_fu:,} orders have no fulfilment unit.")
    if missing_items:
        r.add("MAJOR", f"{missing_items:,} orders have no order-item rows.")
    if bad_delivery:
        r.add("CRITICAL", f"{bad_delivery:,} fulfilment units do not have exactly one delivery.")

    avg_fu = len(fus) / len(orders) if orders else 0
    avg_items = len(items) / len(orders) if orders else 0
    r.metrics["Fulfilments / order"] = round(avg_fu, 3)
    r.metrics["Item rows / order"] = round(avg_items, 3)
    r.metrics["Deliveries / fulfilment"] = round(len(deliveries) / len(fus), 3) if fus else 0

    if avg_fu > MAX_FU_PER_ORDER:
        r.add("MAJOR", f"Average fulfilments/order is {avg_fu:.2f}; unusually high for this model.")
    if avg_items < 1:
        r.add("MAJOR", "Average order-item rows/order is below 1.")

    bad_quantity = 0
    for row in items:
        try:
            if int(row.get("quantity", "")) <= 0:
                bad_quantity += 1
        except ValueError:
            bad_quantity += 1
    if bad_quantity:
        r.add("CRITICAL", f"{bad_quantity:,} order-item rows have invalid/non-positive quantity.")


def check_demand(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    by_day, by_hour, by_customer, by_store = Counter(), Counter(), Counter(), Counter()
    for row in data["orders"]:
        t = parse_ts(row.get("created_at"))
        if t:
            by_day[t.date()] += 1
            by_hour[t.hour] += 1
        by_customer[row.get("customer_id", "")] += 1
    for row in data["fulfilment_units"]:
        by_store[row.get("store_id", "")] += 1

    total_orders = len(data["orders"])
    if by_day:
        day, n = by_day.most_common(1)[0]
        share = n / total_orders if total_orders else 0
        r.metrics["Busiest day share"] = f"{share:.2%} ({day})"
        if share > MAX_DAY_SHARE:
            r.add("MAJOR", f"Busiest day contains {share:.1%} of orders; artificial concentration is likely.")

    if by_hour:
        hour, n = by_hour.most_common(1)[0]
        share = n / total_orders if total_orders else 0
        r.metrics["Busiest hour share"] = f"{share:.2%} ({hour:02d}:00)"
        if share > MAX_HOUR_SHARE:
            r.add("MAJOR", f"Hour {hour:02d}:00 contains {share:.1%} of orders; inspect hourly allocation.")

    if by_store and data["fulfilment_units"]:
        store, n = by_store.most_common(1)[0]
        share = n / len(data["fulfilment_units"])
        r.metrics["Largest store fulfilment share"] = f"{share:.2%} ({store})"
        if share > MAX_STORE_SHARE:
            r.add("MAJOR", f"Store {store} handles {share:.1%} of fulfilments; inspect store allocation.")

    counts = list(by_customer.values())
    if counts:
        r.metrics["Ordering customers"] = len(counts)
        r.metrics["Average orders / ordering customer"] = round(sum(counts) / len(counts), 3)
        r.metrics["Max orders by one customer"] = max(counts)
        if max(counts) > MAX_ORDERS_ONE_CUSTOMER:
            r.add("MINOR", f"One customer has {max(counts)} orders in the simulation window.")


def check_assignments(data: dict[str, list[dict[str, str]]], r: Result) -> dict[str, set[str]]:
    accepted: dict[str, set[str]] = defaultdict(set)
    for row in data["rider_assignments"]:
        aid = row.get("assignment_id", "")
        response = row.get("response", "")
        offered = parse_ts(row.get("offered_at"))
        responded = parse_ts(row.get("responded_at"))
        expired = parse_ts(row.get("expired_at"))

        if response == "ACCEPTED":
            accepted[row.get("delivery_id", "")].add(row.get("rider_id", ""))
            if not responded or expired:
                r.add("CRITICAL", f"Accepted assignment {aid} has invalid response timestamps.")
        elif response == "REJECTED":
            if not responded or expired or not row.get("rejection_reason"):
                r.add("CRITICAL", f"Rejected assignment {aid} has invalid responded/expired/rejection fields.")
        elif response == "EXPIRED":
            if responded:
                r.add("CRITICAL", f"Expired assignment {aid} has responded_at populated; it should be NULL.")
            if not expired:
                r.add("CRITICAL", f"Expired assignment {aid} has no expired_at.")
            if row.get("rejection_reason"):
                r.add("MINOR", f"Expired assignment {aid} has rejection_reason populated.")
        else:
            r.add("CRITICAL", f"Assignment {aid} has unsupported response={response!r}.")

        terminal = responded or expired
        if offered and terminal and terminal < offered:
            r.add("CRITICAL", f"Assignment {aid} terminates before offered_at.")

    multi = {delivery: riders for delivery, riders in accepted.items() if len(riders) > 1}
    if multi:
        r.add("CRITICAL", f"{len(multi):,} deliveries have more than one accepted rider.")

    r.metrics["Assignment attempts"] = len(data["rider_assignments"])
    r.metrics["Accepted deliveries"] = sum(bool(x) for x in accepted.values())
    return accepted


def check_events(
    data: dict[str, list[dict[str, str]]],
    accepted: dict[str, set[str]],
    r: Result,
) -> None:
    orders = {x["order_id"] for x in data["orders"]}
    fus = {x["fulfilment_unit_id"] for x in data["fulfilment_units"]}
    deliveries = {x["delivery_id"] for x in data["deliveries"]}

    event_types_by_delivery: dict[str, set[str]] = defaultdict(set)
    event_types_by_fu: dict[str, set[str]] = defaultdict(set)
    rider_assigned: dict[str, set[str]] = defaultdict(set)
    last_time: dict[str, datetime] = {}
    last_stage: dict[str, int] = {}

    for event in data["operational_events"]:
        eid = event.get("event_id", "")
        oid = event.get("order_id", "")
        fid = event.get("fulfilment_unit_id", "")
        did = event.get("delivery_id", "")
        rid = event.get("rider_id", "")
        event_type = event.get("event_type", "")

        if oid and oid not in orders:
            r.add("CRITICAL", f"Event {eid} references nonexistent order {oid}.")
        if fid and fid not in fus:
            r.add("CRITICAL", f"Event {eid} references nonexistent fulfilment {fid}.")
        if did and did not in deliveries:
            r.add("CRITICAL", f"Event {eid} references nonexistent delivery {did}.")

        occurred = parse_ts(event.get("occurred_at"))
        if not occurred:
            r.add("CRITICAL", f"Event {eid} has invalid occurred_at.")
            continue

        if did:
            event_types_by_delivery[did].add(event_type)
            if did in last_time and occurred < last_time[did]:
                r.add("CRITICAL", f"Delivery {did} has backwards event time.")
            last_time[did] = occurred

            stage = EVENT_STAGE.get(event_type)
            if stage is not None:
                prev = last_stage.get(did)
                if prev is not None and stage < prev:
                    r.add("CRITICAL", f"Delivery {did} has impossible lifecycle order around {event_type}.")
                last_stage[did] = max(prev or stage, stage)

        if fid:
            event_types_by_fu[fid].add(event_type)

        if event_type == "RIDER_ASSIGNED":
            rider_assigned[did].add(rid)

    # Accepted assignment -> exactly matching RIDER_ASSIGNED event.
    for did, accepted_riders in accepted.items():
        if rider_assigned.get(did, set()) != accepted_riders:
            r.add(
                "CRITICAL",
                f"Delivery {did}: accepted rider(s) {sorted(accepted_riders)} do not exactly match RIDER_ASSIGNED rider(s) {sorted(rider_assigned.get(did, set()))}.",
            )

    # Terminal delivery event requirements.
    for delivery in data["deliveries"]:
        did = delivery["delivery_id"]
        status = delivery.get("status", "")
        events = event_types_by_delivery.get(did, set())
        fu_id = delivery.get("fulfilment_unit_id", "")

        if status == "DELIVERED":
            required = {"RIDER_ASSIGNED", "RIDER_ARRIVED_AT_STORE", "PICKED_UP", "DELIVERY_STARTED", "DELIVERED"}
            missing = required - events
            if missing:
                r.add("CRITICAL", f"Delivered delivery {did} is missing events {sorted(missing)}.")

        elif status == "FAILED":
            # Failure can terminate at fulfilment level or delivery level.
            if not ({"DELIVERY_FAILED", "FULFILMENT_FAILED"} & (events | event_types_by_fu.get(fu_id, set()))):
                r.add("CRITICAL", f"Failed delivery {did} has no corresponding failure event.")

        elif status == "CANCELLED":
            # IMPORTANT: cancellation is recorded against the FU, not the delivery.
            if "FULFILMENT_CANCELLED" not in event_types_by_fu.get(fu_id, set()):
                r.add("MAJOR", f"Cancelled delivery {did} -> fulfilment {fu_id} has no FULFILMENT_CANCELLED event.")

    r.metrics["Operational events"] = len(data["operational_events"])
    r.metrics["Events / delivery"] = round(len(data["operational_events"]) / len(deliveries), 3) if deliveries else 0


def check_states(data: dict[str, list[dict[str, str]]], accepted: dict[str, set[str]], r: Result) -> None:
    fus = {x["fulfilment_unit_id"]: x for x in data["fulfilment_units"]}
    deliveries = {x["delivery_id"]: x for x in data["deliveries"]}

    for delivery in deliveries.values():
        fu = fus.get(delivery.get("fulfilment_unit_id", ""))
        if not fu:
            continue

        d_status = delivery.get("status", "")
        f_status = fu.get("status", "")
        expected = {"DELIVERED": "COMPLETED", "FAILED": "FAILED", "CANCELLED": "CANCELLED"}.get(d_status)
        if expected and f_status != expected:
            r.add("CRITICAL", f"Delivery {delivery['delivery_id']} is {d_status} but fulfilment is {f_status}.")

        if d_status == "DELIVERED":
            required_fields = ["rider_id", "rider_arrived_at_store", "picked_up_at", "delivery_started_at", "delivered_at"]
            missing = [field for field in required_fields if not delivery.get(field)]
            if missing:
                r.add("CRITICAL", f"Delivered delivery {delivery['delivery_id']} is missing fields {missing}.")

        if d_status in {"FAILED", "CANCELLED"} and delivery.get("delivered_at"):
            r.add("CRITICAL", f"Terminal delivery {delivery['delivery_id']} is {d_status} but has delivered_at.")

        if d_status == "REQUESTED" and delivery.get("rider_id"):
            r.add("MAJOR", f"Requested delivery {delivery['delivery_id']} already has rider_id={delivery['rider_id']}.")

    mismatch = 0
    for did, riders in accepted.items():
        delivery = deliveries.get(did)
        if delivery and delivery.get("rider_id") and delivery["rider_id"] not in riders:
            mismatch += 1
    if mismatch:
        r.add("CRITICAL", f"{mismatch:,} deliveries have final rider_id different from accepted assignment rider.")


def check_time_causality(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    orders = {x["order_id"]: x for x in data["orders"]}

    for order in data["orders"]:
        created = parse_ts(order.get("created_at"))
        payment = parse_ts(order.get("payment_success_at"))
        if created and payment and payment < created:
            r.add("CRITICAL", f"Order {order['order_id']} has payment before creation.")

    for fu in data["fulfilment_units"]:
        pairs = [
            ("assigned_to_store_at", "picking_started_at"),
            ("picking_started_at", "picking_completed_at"),
            ("picking_completed_at", "packing_started_at"),
            ("packing_started_at", "packing_completed_at"),
        ]
        for left, right in pairs:
            a, b = parse_ts(fu.get(left)), parse_ts(fu.get(right))
            if a and b and b < a:
                r.add("CRITICAL", f"Fulfilment {fu['fulfilment_unit_id']} has {right} before {left}.")

        order = orders.get(fu.get("order_id", ""))
        payment = parse_ts(order.get("payment_success_at")) if order else None
        assigned = parse_ts(fu.get("assigned_to_store_at"))
        if payment and assigned and assigned < payment:
            r.add("CRITICAL", f"Fulfilment {fu['fulfilment_unit_id']} is assigned before payment succeeds.")

        status = fu.get("status", "")
        terminal = parse_ts(fu.get("cancelled_at")) or parse_ts(fu.get("failed_at")) or parse_ts(fu.get("completed_at"))
        if status in TERMINAL_FU and not terminal:
            r.add("CRITICAL", f"Fulfilment {fu['fulfilment_unit_id']} is {status} but has no terminal timestamp.")

    for delivery in data["deliveries"]:
        pairs = [
            ("rider_arrived_at_store", "picked_up_at"),
            ("picked_up_at", "delivery_started_at"),
            ("delivery_started_at", "delivered_at"),
        ]
        for left, right in pairs:
            a, b = parse_ts(delivery.get(left)), parse_ts(delivery.get(right))
            if a and b and b < a:
                r.add("CRITICAL", f"Delivery {delivery['delivery_id']} has {right} before {left}.")


def check_order_rollup(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    """
    Validate the CURRENT simulator's intentional pessimistic precedence rule.

    statuses == {COMPLETED} -> DELIVERED
    elif contains CANCELLED   -> CANCELLED
    elif contains FAILED      -> FAILED
    else                      -> FULFILLING

    We do not impose PARTIALLY_FULFILLED.
    """
    by_order: dict[str, list[str]] = defaultdict(list)
    for fu in data["fulfilment_units"]:
        by_order[fu["order_id"]].append(fu.get("status", ""))

    for order in data["orders"]:
        statuses = by_order.get(order["order_id"], [])
        if not statuses:
            r.add("CRITICAL", f"Order {order['order_id']} has no fulfilment units.")
            continue

        expected: str
        if all(s == "COMPLETED" for s in statuses):
            expected = "DELIVERED"
        elif "CANCELLED" in statuses:
            expected = "CANCELLED"
        elif "FAILED" in statuses:
            expected = "FAILED"
        else:
            expected = "FULFILLING"

        actual = order.get("status", "")
        if actual != expected:
            r.add(
                "CRITICAL",
                f"Order {order['order_id']} has fulfilment statuses {statuses} but parent status={actual!r}; expected {expected!r} under the simulator's defined roll-up rule.",
            )


def check_rider_concurrency(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    by_rider: dict[str, list[tuple[datetime, datetime, str]]] = defaultdict(list)
    for delivery in data["deliveries"]:
        rider = delivery.get("rider_id", "")
        if delivery.get("status") != "DELIVERED" or not rider:
            continue
        start = parse_ts(delivery.get("rider_arrived_at_store")) or parse_ts(delivery.get("picked_up_at")) or parse_ts(delivery.get("delivery_started_at"))
        end = parse_ts(delivery.get("delivered_at"))
        if start and end and end >= start:
            by_rider[rider].append((start, end, delivery["delivery_id"]))

    overlaps = 0
    max_active = 0
    for trips in by_rider.values():
        trips.sort(key=lambda x: x[0])
        active: list[tuple[datetime, datetime, str]] = []
        for start, end, _ in trips:
            active = [x for x in active if x[1] > start]
            overlaps += len(active)
            max_active = max(max_active, len(active) + 1 if active else 1)
            active.append((start, end, _))

    r.metrics["Rider overlapping-delivery pairs"] = overlaps
    r.metrics["Max concurrent deliveries / rider"] = max_active
    if overlaps:
        r.add("CRITICAL", f"{overlaps:,} overlapping delivery intervals detected for riders.")


def check_staffing(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    rows = data["store_staffing"]
    keys = Counter((x.get("store_id", ""), x.get("recorded_at", "")) for x in rows)
    duplicates = sum(n - 1 for n in keys.values() if n > 1)
    if duplicates:
        r.add("CRITICAL", f"{duplicates:,} duplicate store/hour staffing snapshots.")

    invalid = 0
    picker_equal = packer_equal = 0
    for row in rows:
        try:
            ps = int(row.get("pickers_scheduled", ""))
            pa = int(row.get("pickers_available", ""))
            ks = int(row.get("packers_scheduled", ""))
            ka = int(row.get("packers_available", ""))
        except ValueError:
            invalid += 1
            continue

        if min(ps, pa, ks, ka) < 0 or pa > ps or ka > ks:
            invalid += 1
        picker_equal += pa == ps
        packer_equal += ka == ks

    if invalid:
        r.add("CRITICAL", f"{invalid:,} staffing rows have invalid counts or available > scheduled.")

    if rows:
        p1 = picker_equal / len(rows)
        p2 = packer_equal / len(rows)
        r.metrics["Picker scheduled=available"] = f"{p1:.1%}"
        r.metrics["Packer scheduled=available"] = f"{p2:.1%}"
        if p1 >= 0.95:
            r.add("MINOR", f"{p1:.1%} of staffing snapshots have picker availability equal to scheduled staff.")
        if p2 >= 0.95:
            r.add("MINOR", f"{p2:.1%} of staffing snapshots have packer availability equal to scheduled staff.")


def check_delivery_realism(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    distances: list[float] = []
    transits: list[float] = []
    traffic = Counter()
    weather = Counter()
    statuses = Counter()

    for d in data["deliveries"]:
        statuses[d.get("status", "")] += 1
        distance = num(d.get("delivery_distance"))
        if distance is not None:
            distances.append(distance)
        if d.get("traffic_condition"):
            traffic[d["traffic_condition"]] += 1
        if d.get("weather_condition"):
            weather[d["weather_condition"]] += 1

        start = parse_ts(d.get("delivery_started_at")) or parse_ts(d.get("picked_up_at"))
        end = parse_ts(d.get("delivered_at"))
        if start and end and end >= start:
            transits.append((end - start).total_seconds() / 60)

    if distances:
        r.metrics["Delivery distance median"] = f"{median(distances):.2f} km"
        r.metrics["Delivery distance p95"] = f"{percentile(distances, .95):.2f} km"
        too_far = sum(x > MAX_DISTANCE_KM for x in distances)
        nonpositive = sum(x <= 0 for x in distances)
        if too_far:
            r.add("MAJOR", f"{too_far:,} delivery distances exceed {MAX_DISTANCE_KM} km for the intended quick-commerce radius.")
        if nonpositive:
            r.add("CRITICAL", f"{nonpositive:,} deliveries have non-positive distance.")

    if transits:
        r.metrics["Transit median"] = f"{median(transits):.2f} min"
        r.metrics["Transit p95"] = f"{percentile(transits, .95):.2f} min"
        if any(x <= 0 for x in transits):
            r.add("CRITICAL", "At least one delivered trip has non-positive transit duration.")

    r.metrics["Delivery statuses"] = dict(statuses)
    r.metrics["Traffic categories"] = dict(traffic)
    r.metrics["Weather categories"] = dict(weather)
    if len(traffic) <= 1:
        r.add("MINOR", "Traffic has only one category; segmentation has little analytical value.")
    if len(weather) <= 1:
        r.add("MINOR", "Weather has only one category; weather segmentation has little analytical value.")


def check_sla(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    orders = {x["order_id"]: x for x in data["orders"]}
    deliveries = {x["fulfilment_unit_id"]: x for x in data["deliveries"]}
    durations: list[float] = []
    on_target = grace = breach = 0

    for fu in data["fulfilment_units"]:
        d = deliveries.get(fu["fulfilment_unit_id"])
        o = orders.get(fu.get("order_id", ""))
        if not d or not o or d.get("status") != "DELIVERED":
            continue
        payment = parse_ts(o.get("payment_success_at"))
        delivered = parse_ts(d.get("delivered_at"))
        if not payment or not delivered:
            r.add("CRITICAL", f"Delivered delivery {d['delivery_id']} cannot produce payment-success-to-delivery SLA duration.")
            continue
        if delivered < payment:
            r.add("CRITICAL", f"Delivery {d['delivery_id']} completes before payment_success_at.")
            continue
        minutes = (delivered - payment).total_seconds() / 60
        durations.append(minutes)
        if minutes <= SLA_TARGET:
            on_target += 1
        elif minutes <= SLA_TARGET + SLA_GRACE:
            grace += 1
        else:
            breach += 1

    total = on_target + grace + breach
    r.metrics["SLA on target"] = pct(on_target, total)
    r.metrics["SLA within grace"] = pct(grace, total)
    r.metrics["SLA breach"] = pct(breach, total)
    if durations:
        r.metrics["SLA median"] = f"{median(durations):.2f} min"
        r.metrics["SLA p95"] = f"{percentile(durations, .95):.2f} min"

    # This is deliberately a realism warning, not a logical failure.
    if total and breach / total >= 0.50:
        r.add("MAJOR", f"{breach / total:.1%} of delivered operations breach the {SLA_TARGET + SLA_GRACE}-minute threshold; review the operational story.")


def check_obvious_values(data: dict[str, list[dict[str, str]]], r: Result) -> None:
    for store in data["stores"]:
        capacity = num(store.get("baseline_capacity"))
        if capacity is None or capacity <= 0:
            r.add("CRITICAL", f"Store {store.get('store_id')} has invalid baseline_capacity.")
        if store.get("status") == "ACTIVE" and store.get("closed_at"):
            r.add("MAJOR", f"Store {store.get('store_id')} is ACTIVE but has closed_at.")

    for rider in data["riders"]:
        if rider.get("status") == "ACTIVE" and rider.get("deactivated_at"):
            r.add("MAJOR", f"Rider {rider.get('rider_id')} is ACTIVE but has deactivated_at.")

    for delivery in data["deliveries"]:
        if not delivery.get("traffic_condition") or not delivery.get("weather_condition"):
            r.add("MAJOR", f"Delivery {delivery.get('delivery_id')} is missing traffic/weather condition.")
        if delivery.get("status") == "DELIVERED" and not delivery.get("delivered_at"):
            r.add("CRITICAL", f"Delivered delivery {delivery.get('delivery_id')} has no delivered_at.")


def audit(dataset_dir: Path) -> Result:
    r = Result()
    data = load(dataset_dir, r)
    check_columns(data, r)
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

    result.report(dataset_dir)
    return 1 if result.critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
