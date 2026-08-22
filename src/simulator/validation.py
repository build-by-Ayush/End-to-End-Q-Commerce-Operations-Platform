from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from simulator.state import SimulationState
from simulator.time_utils import parse_timestamp


TIMESTAMP_FIELDS = {
    "created_at",
    "payment_success_at",
    "assigned_to_store_at",
    "picking_started_at",
    "picking_completed_at",
    "packing_started_at",
    "packing_completed_at",
    "cancelled_at",
    "failed_at",
    "completed_at",
    "rider_arrived_at_store",
    "picked_up_at",
    "delivery_started_at",
    "delivered_at",
    "offered_at",
    "responded_at",
    "expired_at",
    "occurred_at",
}


class ValidationResult:
    """Collect validation errors and warnings."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def print_report(self) -> None:
        print("\n" + "=" * 60)
        print("SIMULATION VALIDATION REPORT")
        print("=" * 60)

        if self.errors:
            print(f"\nERRORS: {len(self.errors)}")

            for error in self.errors:
                print(f"  [ERROR] {error}")
        else:
            print("\nERRORS: 0")

        if self.warnings:
            print(f"\nWARNINGS: {len(self.warnings)}")

            for warning in self.warnings:
                print(f"  [WARNING] {warning}")
        else:
            print("WARNINGS: 0")

        print()

        if self.passed:
            print("VALIDATION RESULT: PASS")
        else:
            print("VALIDATION RESULT: FAIL")

        print("=" * 60)


def parse_optional_timestamp(
    value: str | None,
) -> datetime | None:
    """Parse a nullable simulator timestamp."""

    if value is None:
        return None

    if value == "":
        return None

    return parse_timestamp(value)


def validate_unique_ids(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate uniqueness of primary/business identifiers."""

    datasets = {
        "customers": (
            state.customers,
            "customer_id",
        ),
        "stores": (
            state.stores,
            "store_id",
        ),
        "riders": (
            state.riders,
            "rider_id",
        ),
        "orders": (
            state.orders,
            "order_id",
        ),
        "fulfilment_units": (
            state.fulfilment_units,
            "fulfilment_unit_id",
        ),
        "order_items": (
            state.order_items,
            "order_item_id",
        ),
        "deliveries": (
            state.deliveries,
            "delivery_id",
        ),
        "rider_assignments": (
            state.rider_assignments,
            "assignment_id",
        ),
        "operational_events": (
            state.operational_events,
            "event_id",
        ),
        "store_staffing": (
            state.store_staffing,
            "staffing_snapshot_id",
        ),
    }

    for dataset_name, (
        rows,
        id_column,
    ) in datasets.items():

        seen: set[str] = set()

        for row in rows:
            identifier = row.get(id_column)

            if not identifier:
                result.error(
                    f"{dataset_name}: missing {id_column}"
                )
                continue

            if identifier in seen:
                result.error(
                    f"{dataset_name}: duplicate "
                    f"{id_column}={identifier}"
                )

            seen.add(identifier)


def validate_foreign_keys(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate mandatory parent-child relationships."""

    customer_ids = {
        row["customer_id"]
        for row in state.customers
    }

    store_ids = {
        row["store_id"]
        for row in state.stores
    }

    rider_ids = {
        row["rider_id"]
        for row in state.riders
    }

    order_ids = {
        row["order_id"]
        for row in state.orders
    }

    fulfilment_ids = {
        row["fulfilment_unit_id"]
        for row in state.fulfilment_units
    }

    delivery_ids = {
        row["delivery_id"]
        for row in state.deliveries
    }

    for row in state.orders:

        if row["customer_id"] not in customer_ids:
            result.error(
                "orders: unknown customer_id "
                f"{row['customer_id']} for "
                f"{row['order_id']}"
            )

    for row in state.fulfilment_units:

        if row["order_id"] not in order_ids:
            result.error(
                "fulfilment_units: unknown order_id "
                f"{row['order_id']} for "
                f"{row['fulfilment_unit_id']}"
            )

        if row["store_id"] not in store_ids:
            result.error(
                "fulfilment_units: unknown store_id "
                f"{row['store_id']} for "
                f"{row['fulfilment_unit_id']}"
            )

    for row in state.order_items:

        if row["order_id"] not in order_ids:
            result.error(
                "order_items: unknown order_id "
                f"{row['order_id']} for "
                f"{row['order_item_id']}"
            )

        if (
            row["fulfilment_unit_id"]
            not in fulfilment_ids
        ):
            result.error(
                "order_items: unknown "
                "fulfilment_unit_id "
                f"{row['fulfilment_unit_id']} for "
                f"{row['order_item_id']}"
            )

    for row in state.deliveries:

        if (
            row["fulfilment_unit_id"]
            not in fulfilment_ids
        ):
            result.error(
                "deliveries: unknown "
                "fulfilment_unit_id "
                f"{row['fulfilment_unit_id']} for "
                f"{row['delivery_id']}"
            )

        rider_id = row.get("rider_id")

        if rider_id and rider_id not in rider_ids:
            result.error(
                "deliveries: unknown rider_id "
                f"{rider_id} for "
                f"{row['delivery_id']}"
            )

    for row in state.rider_assignments:

        if row["delivery_id"] not in delivery_ids:
            result.error(
                "rider_assignments: unknown "
                "delivery_id "
                f"{row['delivery_id']} for "
                f"{row['assignment_id']}"
            )

        if row["rider_id"] not in rider_ids:
            result.error(
                "rider_assignments: unknown rider_id "
                f"{row['rider_id']} for "
                f"{row['assignment_id']}"
            )

    for row in state.operational_events:

        optional_references = {
            "order_id": order_ids,
            "fulfilment_unit_id": fulfilment_ids,
            "delivery_id": delivery_ids,
            "store_id": store_ids,
            "rider_id": rider_ids,
        }

        for column, valid_ids in optional_references.items():

            value = row.get(column)

            if value and value not in valid_ids:
                result.error(
                    "operational_events: unknown "
                    f"{column}={value} for "
                    f"{row['event_id']}"
                )

    for row in state.store_staffing:

        if row["store_id"] not in store_ids:
            result.error(
                "store_staffing: unknown store_id "
                f"{row['store_id']} for "
                f"{row['staffing_snapshot_id']}"
            )


def validate_order_item_ownership(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Ensure an order item belongs to a fulfilment unit
    whose parent order is the same order.
    """

    fulfilments_by_id = {
        row["fulfilment_unit_id"]: row
        for row in state.fulfilment_units
    }

    for item in state.order_items:

        fulfilment = fulfilments_by_id.get(
            item["fulfilment_unit_id"]
        )

        if fulfilment is None:
            continue

        if (
            fulfilment["order_id"]
            != item["order_id"]
        ):
            result.error(
                "order_items: order/fulfilment mismatch "
                f"for {item['order_item_id']} - "
                f"order_id={item['order_id']}, "
                f"fulfilment belongs to "
                f"{fulfilment['order_id']}"
            )


def validate_fulfilment_item_coverage(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Every fulfilment unit representing active work should
    have at least one order item.
    """

    item_count_by_fulfilment = defaultdict(int)

    for item in state.order_items:
        item_count_by_fulfilment[
            item["fulfilment_unit_id"]
        ] += 1

    for fulfilment in state.fulfilment_units:

        fulfilment_id = (
            fulfilment["fulfilment_unit_id"]
        )

        item_count = item_count_by_fulfilment.get(
            fulfilment_id,
            0,
        )

        if item_count == 0:
            result.error(
                "fulfilment_units: fulfilment unit "
                f"{fulfilment_id} has no order items"
            )


def validate_timestamps(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Validate that timestamps can be parsed.

    Ordering is checked separately.
    """

    datasets = [
        (
            "orders",
            state.orders,
            [
                "created_at",
                "payment_success_at",
                "cancelled_at",
            ],
        ),
        (
            "fulfilment_units",
            state.fulfilment_units,
            [
                "assigned_to_store_at",
                "picking_started_at",
                "picking_completed_at",
                "packing_started_at",
                "packing_completed_at",
                "cancelled_at",
                "failed_at",
                "completed_at",
            ],
        ),
        (
            "deliveries",
            state.deliveries,
            [
                "rider_arrived_at_store",
                "picked_up_at",
                "delivery_started_at",
                "delivered_at",
                "cancelled_at",
                "failed_at",
            ],
        ),
        (
            "rider_assignments",
            state.rider_assignments,
            [
                "offered_at",
                "responded_at",
                "expired_at",
            ],
        ),
        (
            "operational_events",
            state.operational_events,
            [
                "occurred_at",
            ],
        ),
        (
            "store_staffing",
            state.store_staffing,
            [
                "recorded_at",
            ],
        ),
    ]

    for dataset_name, rows, columns in datasets:

        for row in rows:

            for column in columns:

                value = row.get(column)

                if not value:
                    continue

                try:
                    parse_timestamp(value)

                except ValueError:
                    result.error(
                        f"{dataset_name}: invalid "
                        f"timestamp {column}="
                        f"{value!r}"
                    )


def validate_order_lifecycle(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate basic order-level timestamp ordering."""

    for order in state.orders:

        created_at = parse_optional_timestamp(
            order.get("created_at")
        )

        payment_success_at = (
            parse_optional_timestamp(
                order.get(
                    "payment_success_at"
                )
            )
        )

        if (
            created_at is not None
            and payment_success_at is not None
            and payment_success_at < created_at
        ):
            result.error(
                "orders: payment_success_at "
                f"occurs before created_at for "
                f"{order['order_id']}"
            )

        status = order.get("status")

        if status == "DELIVERED":

            if order.get("cancelled_at"):
                result.error(
                    "orders: delivered order has "
                    f"cancelled_at for "
                    f"{order['order_id']}"
                )

            if order.get("cancellation_reason"):
                result.error(
                    "orders: delivered order has "
                    "cancellation_reason for "
                    f"{order['order_id']}"
                )

            if order.get("failure_reason"):
                result.error(
                    "orders: delivered order has "
                    "failure_reason for "
                    f"{order['order_id']}"
                )


def validate_fulfilment_lifecycle(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate fulfilment timestamp ordering and status."""

    for fulfilment in state.fulfilment_units:

        values = [
            (
                "assigned_to_store_at",
                fulfilment.get(
                    "assigned_to_store_at"
                ),
            ),
            (
                "picking_started_at",
                fulfilment.get(
                    "picking_started_at"
                ),
            ),
            (
                "picking_completed_at",
                fulfilment.get(
                    "picking_completed_at"
                ),
            ),
            (
                "packing_started_at",
                fulfilment.get(
                    "packing_started_at"
                ),
            ),
            (
                "packing_completed_at",
                fulfilment.get(
                    "packing_completed_at"
                ),
            ),
            (
                "completed_at",
                fulfilment.get(
                    "completed_at"
                ),
            ),
        ]

        previous_name: str | None = None
        previous_value: datetime | None = None

        for name, raw_value in values:

            current_value = parse_optional_timestamp(
                raw_value
            )

            if current_value is None:
                continue

            if (
                previous_value is not None
                and current_value < previous_value
            ):
                result.error(
                    "fulfilment_units: timestamp "
                    f"ordering error for "
                    f"{fulfilment['fulfilment_unit_id']}: "
                    f"{previous_name} > {name}"
                )

            previous_name = name
            previous_value = current_value

        status = fulfilment.get("status")

        if status == "COMPLETED":

            if not fulfilment.get(
                "completed_at"
            ):
                result.error(
                    "fulfilment_units: COMPLETED "
                    f"unit has no completed_at: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

        if status == "CANCELLED":

            if not fulfilment.get(
                "cancelled_at"
            ):
                result.error(
                    "fulfilment_units: CANCELLED "
                    f"unit has no cancelled_at: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

            if not fulfilment.get(
                "cancellation_reason"
            ):
                result.error(
                    "fulfilment_units: CANCELLED "
                    f"unit has no cancellation_reason: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

        if status == "FAILED":

            if not fulfilment.get(
                "failed_at"
            ):
                result.error(
                    "fulfilment_units: FAILED "
                    f"unit has no failed_at: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )

            if not fulfilment.get(
                "failure_reason"
            ):
                result.error(
                    "fulfilment_units: FAILED "
                    f"unit has no failure_reason: "
                    f"{fulfilment['fulfilment_unit_id']}"
                )


def validate_delivery_lifecycle(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate delivery status and timestamp consistency."""

    for delivery in state.deliveries:

        delivery_id = delivery["delivery_id"]
        status = delivery["status"]

        rider_arrived = parse_optional_timestamp(
            delivery.get(
                "rider_arrived_at_store"
            )
        )

        picked_up = parse_optional_timestamp(
            delivery.get("picked_up_at")
        )

        delivery_started = (
            parse_optional_timestamp(
                delivery.get(
                    "delivery_started_at"
                )
            )
        )

        delivered = parse_optional_timestamp(
            delivery.get("delivered_at")
        )

        if (
            rider_arrived is not None
            and picked_up is not None
            and picked_up < rider_arrived
        ):
            result.error(
                "deliveries: picked_up_at occurs "
                f"before rider_arrived_at_store "
                f"for {delivery_id}"
            )

        if (
            picked_up is not None
            and delivery_started is not None
            and delivery_started < picked_up
        ):
            result.error(
                "deliveries: delivery_started_at "
                "occurs before picked_up_at for "
                f"{delivery_id}"
            )

        if (
            delivery_started is not None
            and delivered is not None
            and delivered < delivery_started
        ):
            result.error(
                "deliveries: delivered_at occurs "
                "before delivery_started_at for "
                f"{delivery_id}"
            )

        if status == "DELIVERED":

            required_fields = [
                "rider_id",
                "rider_arrived_at_store",
                "picked_up_at",
                "delivery_started_at",
                "delivered_at",
            ]

            for field in required_fields:

                if not delivery.get(field):
                    result.error(
                        "deliveries: DELIVERED delivery "
                        f"{delivery_id} missing "
                        f"{field}"
                    )

        if status == "FAILED":

            if not delivery.get(
                "failed_at"
            ):
                result.error(
                    "deliveries: FAILED delivery "
                    f"{delivery_id} missing failed_at"
                )

            if not delivery.get(
                "failure_reason"
            ):
                result.error(
                    "deliveries: FAILED delivery "
                    f"{delivery_id} missing "
                    "failure_reason"
                )

        if status == "CANCELLED":

            if not delivery.get(
                "cancelled_at"
            ):
                result.error(
                    "deliveries: CANCELLED delivery "
                    f"{delivery_id} missing "
                    "cancelled_at"
                )

            if not delivery.get(
                "cancellation_reason"
            ):
                result.error(
                    "deliveries: CANCELLED delivery "
                    f"{delivery_id} missing "
                    "cancellation_reason"
                )


def validate_assignment_semantics(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate accepted/rejected/expired rider offers."""

    for assignment in state.rider_assignments:

        response = assignment["response"]

        responded_at = assignment.get(
            "responded_at"
        )

        expired_at = assignment.get(
            "expired_at"
        )

        if response == "ACCEPTED":

            if not responded_at:
                result.error(
                    "rider_assignments: ACCEPTED "
                    f"assignment {assignment['assignment_id']} "
                    "has no responded_at"
                )

            if expired_at:
                result.error(
                    "rider_assignments: ACCEPTED "
                    f"assignment {assignment['assignment_id']} "
                    "has expired_at"
                )

        elif response == "REJECTED":

            if not responded_at:
                result.error(
                    "rider_assignments: REJECTED "
                    f"assignment {assignment['assignment_id']} "
                    "has no responded_at"
                )

            if expired_at:
                result.error(
                    "rider_assignments: REJECTED "
                    f"assignment {assignment['assignment_id']} "
                    "has expired_at"
                )

            if not assignment.get(
                "rejection_reason"
            ):
                result.error(
                    "rider_assignments: REJECTED "
                    f"assignment {assignment['assignment_id']} "
                    "has no rejection_reason"
                )

        elif response == "EXPIRED":

            if responded_at:
                result.error(
                    "rider_assignments: EXPIRED "
                    f"assignment {assignment['assignment_id']} "
                    "should not have responded_at"
                )

            if not expired_at:
                result.error(
                    "rider_assignments: EXPIRED "
                    f"assignment {assignment['assignment_id']} "
                    "has no expired_at"
                )


def validate_assignment_events(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Validate that accepted assignments become
    RIDER_ASSIGNED events.
    """

    accepted_assignments = [
        assignment
        for assignment in state.rider_assignments
        if assignment["response"] == "ACCEPTED"
    ]

    rider_assigned_events = [
        event
        for event in state.operational_events
        if event["event_type"]
        == "RIDER_ASSIGNED"
    ]

    events_by_delivery: dict[
        str,
        list[dict],
    ] = defaultdict(list)

    for event in rider_assigned_events:
        events_by_delivery[
            event["delivery_id"]
        ].append(event)

    for assignment in accepted_assignments:

        matching_events = [
            event
            for event in events_by_delivery[
                assignment["delivery_id"]
            ]
            if event["rider_id"]
            == assignment["rider_id"]
        ]

        if len(matching_events) != 1:
            result.error(
                "rider_assignments: accepted "
                f"assignment {assignment['assignment_id']} "
                "does not map to exactly one "
                "matching RIDER_ASSIGNED event"
            )


def validate_delivery_fulfilment_consistency(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate delivery/fulfilment final-state consistency."""

    fulfilments_by_id = {
        row["fulfilment_unit_id"]: row
        for row in state.fulfilment_units
    }

    for delivery in state.deliveries:

        fulfilment = fulfilments_by_id.get(
            delivery["fulfilment_unit_id"]
        )

        if fulfilment is None:
            continue

        delivery_status = delivery["status"]
        fulfilment_status = fulfilment["status"]

        if (
            delivery_status == "DELIVERED"
            and fulfilment_status
            != "COMPLETED"
        ):
            result.error(
                "state mismatch: delivery "
                f"{delivery['delivery_id']} is "
                "DELIVERED but fulfilment "
                f"{fulfilment['fulfilment_unit_id']} "
                f"is {fulfilment_status}"
            )

        if (
            delivery_status == "CANCELLED"
            and fulfilment_status
            != "CANCELLED"
        ):
            result.error(
                "state mismatch: delivery "
                f"{delivery['delivery_id']} is "
                "CANCELLED but fulfilment "
                f"{fulfilment['fulfilment_unit_id']} "
                f"is {fulfilment_status}"
            )

        if (
            delivery_status == "FAILED"
            and fulfilment_status
            != "FAILED"
        ):
            result.error(
                "state mismatch: delivery "
                f"{delivery['delivery_id']} is "
                "FAILED but fulfilment "
                f"{fulfilment['fulfilment_unit_id']} "
                f"is {fulfilment_status}"
            )

        delivery_rider = delivery.get(
            "rider_id"
        )

        if delivery_rider:

            accepted_assignments = [
                assignment
                for assignment
                in state.rider_assignments
                if (
                    assignment["delivery_id"]
                    == delivery["delivery_id"]
                    and assignment["response"]
                    == "ACCEPTED"
                )
            ]

            accepted_riders = {
                assignment["rider_id"]
                for assignment
                in accepted_assignments
            }

            if delivery_rider not in accepted_riders:
                result.error(
                    "state mismatch: delivery "
                    f"{delivery['delivery_id']} has "
                    f"rider_id={delivery_rider}, but "
                    "no matching ACCEPTED assignment"
                )


def validate_event_presence(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """Validate required lifecycle events for final states."""

    events_by_delivery: dict[
        str,
        list[dict],
    ] = defaultdict(list)

    for event in state.operational_events:

        delivery_id = event.get(
            "delivery_id"
        )

        if delivery_id:
            events_by_delivery[
                delivery_id
            ].append(event)

    for delivery in state.deliveries:

        delivery_id = delivery["delivery_id"]
        status = delivery["status"]

        event_types = {
            event["event_type"]
            for event in events_by_delivery[
                delivery_id
            ]
        }

        if status == "DELIVERED":

            required_events = {
                "RIDER_ASSIGNED",
                "RIDER_ARRIVED_AT_STORE",
                "PICKED_UP",
                "DELIVERY_STARTED",
                "DELIVERED",
            }

            missing = (
                required_events
                - event_types
            )

            for event_type in sorted(missing):
                result.error(
                    "deliveries: DELIVERED delivery "
                    f"{delivery_id} missing "
                    f"event {event_type}"
                )

        if status == "FAILED":

            if "DELIVERY_FAILED" not in event_types:
                result.error(
                    "deliveries: FAILED delivery "
                    f"{delivery_id} has no "
                    "DELIVERY_FAILED event"
                )


def validate_rider_concurrency(
    state: SimulationState,
    result: ValidationResult,
) -> None:
    """
    Check that a rider does not have overlapping
    completed delivery intervals.
    """

    deliveries_by_rider: dict[
        str,
        list[tuple[datetime, datetime, str]],
    ] = defaultdict(list)

    for delivery in state.deliveries:

        rider_id = delivery.get("rider_id")

        if not rider_id:
            continue

        start = parse_optional_timestamp(
            delivery.get("delivery_started_at")
        )

        end = parse_optional_timestamp(
            delivery.get("delivered_at")
        )

        if start is None or end is None:
            continue

        deliveries_by_rider[
            rider_id
        ].append(
            (
                start,
                end,
                delivery["delivery_id"],
            )
        )

    for rider_id, intervals in (
        deliveries_by_rider.items()
    ):

        intervals.sort(
            key=lambda item: item[0]
        )

        for index in range(
            1,
            len(intervals),
        ):

            previous_start, previous_end, previous_id = (
                intervals[index - 1]
            )

            current_start, current_end, current_id = (
                intervals[index]
            )

            if current_start < previous_end:
                result.error(
                    "riders: overlapping deliveries "
                    f"for {rider_id}: "
                    f"{previous_id} overlaps "
                    f"{current_id}"
                )


def validate_state(
    state: SimulationState,
) -> ValidationResult:
    """Run the complete clean-data validation suite."""

    result = ValidationResult()

    validate_unique_ids(
        state,
        result,
    )

    validate_foreign_keys(
        state,
        result,
    )

    validate_order_item_ownership(
        state,
        result,
    )

    validate_fulfilment_item_coverage(
        state,
        result,
    )

    validate_timestamps(
        state,
        result,
    )

    validate_order_lifecycle(
        state,
        result,
    )

    validate_fulfilment_lifecycle(
        state,
        result,
    )

    validate_delivery_lifecycle(
        state,
        result,
    )

    validate_assignment_semantics(
        state,
        result,
    )

    validate_assignment_events(
        state,
        result,
    )

    validate_delivery_fulfilment_consistency(
        state,
        result,
    )

    validate_event_presence(
        state,
        result,
    )

    validate_rider_concurrency(
        state,
        result,
    )

    return result