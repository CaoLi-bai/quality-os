# Demo refund specification

## Refundable amount

The cumulative refund amount must not exceed the order paid amount. Amounts are integer cents. A refund equal to the remaining amount is valid. An excessive refund returns HTTP 400 and leaves order state unchanged.

## Idempotency

The client supplies an idempotency key. A retry with the same key and order returns the original refund result without creating another refund or increasing the refunded amount again.

## Authorization

A user can read and refund only their own orders. Cross-user access returns HTTP 403 and must not change state.

## Order state

Only paid and partially refunded orders are refundable. Cancelled or fully refunded orders return HTTP 409.
