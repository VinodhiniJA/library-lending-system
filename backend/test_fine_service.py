
from datetime import datetime, timedelta
from decimal import Decimal

from services.fine_service import calculate_fine


due_at = datetime(2026, 11, 10, 10, 0)

# Returned on time
assert calculate_fine(
    due_at,
    due_at,
    Decimal("5.00"),
    Decimal("100.00")
) == Decimal("0.00")

print("On-time return: PASS")


# Returned 4 days late
assert calculate_fine(
    due_at,
    due_at + timedelta(days=4),
    Decimal("5.00"),
    Decimal("100.00")
) == Decimal("20.00")

print("Four days overdue: PASS")


# Returned 30 days late: maximum cap
assert calculate_fine(
    due_at,
    due_at + timedelta(days=30),
    Decimal("5.00"),
    Decimal("100.00")
) == Decimal("100.00")

print("Maximum fine cap: PASS")


# Returned 1 hour late: one overdue day
assert calculate_fine(
    due_at,
    due_at + timedelta(hours=1),
    Decimal("5.00"),
    Decimal("100.00")
) == Decimal("5.00")

print("Partial overdue day: PASS")
