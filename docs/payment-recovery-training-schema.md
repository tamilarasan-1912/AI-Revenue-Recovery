# Payment Recovery ML Training Schema

The original dataset fields remain required:

| Column | Type | Meaning |
|---|---|---|
| `payment_id` | string | Unique payment identifier |
| `amount` | number | Payment value |
| `failure_reason` | string | Normalized payment failure reason |
| `retry_count` | integer | Previous automatic retry attempts |
| `is_recoverable` | boolean | Supervised target: whether the payment was eventually recoverable |

Recommended historical-behaviour columns:

| Column | Type | Meaning |
|---|---|---|
| `payment_method` | string | UPI/card/netbanking/etc. |
| `decline_code` | string | Provider/issuer decline classification |
| `error_source` | string | bank/gateway/network/etc. |
| `error_step` | string | authorization/capture/etc. |
| `currency` | string | Transaction currency |
| `is_recurring` | boolean | Recurring payment indicator |
| `authentication_required` | boolean | Customer authentication requirement |
| `card_expiry_days` | number | Days until card expiry when relevant |
| `customer_tenure_days` | number | Customer relationship age |
| `previous_payment_success_rate` | number | Historical successful-payment ratio |
| `previous_payment_count` | integer | Historical payment count |
| `previous_failed_payment_count` | integer | Historical failed-payment count |
| `previous_delayed_payment_count` | integer | Historical delayed-payment count |
| `average_payment_delay_days` | number | Mean historical payment delay |
| `days_past_due` | number | Current days past due |
| `outstanding_amount` | number | Current amount still outstanding |
| `reminder_count` | integer | Previous recovery reminders |
| `reminder_response_rate` | number | Historical response-to-reminder ratio |
| `hour_of_day` | integer | Transaction/event hour |
| `day_of_week` | integer | Transaction/event weekday |

Optional regression targets:

- `recovered_amount`: actual recovered amount for the payment.
- `recovery_rate`: actual recovered amount / amount, in the range 0–1.

Never include a future outcome field as an input feature. In particular, `is_recoverable`, `recovered_amount`, and `recovery_rate` are targets/outcomes, not predictors.

## Example

```csv
payment_id,amount,failure_reason,retry_count,payment_method,previous_payment_success_rate,previous_delayed_payment_count,average_payment_delay_days,days_past_due,outstanding_amount,reminder_count,reminder_response_rate,is_recoverable,recovered_amount
pay_001,450,insufficient_funds,1,upi,0.94,1,0.5,1,450,1,1.0,true,450
pay_002,1200,timeout,0,card,0.88,2,1.3,0,1200,0,0.0,true,1200
pay_003,800,expired_card,2,card,0.71,4,3.2,12,800,2,0.0,false,0
```

Use real historical outcomes for production training. Synthetic examples are for development/testing only.
