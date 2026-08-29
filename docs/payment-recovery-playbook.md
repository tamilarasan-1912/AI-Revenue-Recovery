# RecoverAI Payment Recovery Playbook

## Research basis

RecoverAI now follows a provider-neutral version of the recovery lifecycle documented by major payment processors:

1. **Classify the failure before retrying.** Adyen recommends checking the refusal reason and determining whether a payment can be retried. Some final refusal states cannot change. [Adyen payments lifecycle](https://docs.adyen.com/account/payments-lifecycle/)
2. **Use bounded, scheduled retries for potentially temporary failures.** Adyen Auto Rescue retries eligible refused shopper-not-present payments at appropriate times inside a rescue window and reports each retry through webhooks. [Adyen Auto Rescue](https://docs.adyen.com/online-payments/auto-rescue/)
3. **Do not blindly retry fraud or permanent failures.** Adyen's Auto Rescue does not schedule payments that cannot be rescued, including fraud-related refusals. [Adyen Auto Rescue for cards](https://docs.adyen.com/online-payments/auto-rescue/cards)
4. **Move to customer-assisted recovery when retries fail.** Payment links are a documented fallback after unsuccessful rescue. Razorpay also supports payment links by SMS/email and lets customers complete payment with available payment methods. [Razorpay Payment Links](https://razorpay.com/docs/payments/payment-links/how-it-works/)
5. **Support payment-method correction.** Razorpay documents expired cards, blocked cards, insufficient balance and cancelled mandates as payment failure causes, with retry or payment-method-change flows. [Razorpay Payment Retries](https://razorpay.com/docs/payments/subscriptions/payment-retries/)

## RecoverAI implementation

### Failure classes

- `soft_decline`: insufficient funds, timeout, temporary bank/issuer degradation, processing/network errors.
- `hard_decline`: expired/invalid/closed/lost/stolen card, cancelled mandate and other permanent instrument failures.
- `authentication_required`: 3DS/customer/issuer authentication is required.
- `fraud_suspected`: automatic recovery is stopped.
- `retry_exhausted`: bounded retry budget is exhausted.
- `unclassified_failure`: human diagnosis is required.

### Default recovery sequence

| Failure class | Automatic retry | Customer action | Fallback |
|---|---|---|---|
| Soft/temporary | Yes, bounded | Not initially | Payment link after retry budget |
| Hard decline | No | Update/replace payment method | Payment link |
| Authentication | No blind retry | Complete authentication | Authenticated checkout/payment link |
| Fraud | No | Risk review | Stop |
| Retry exhausted | No | Yes | Payment link / human escalation |
| Unknown | No blind retry | Usually | Human diagnosis |

The default simulation schedule is **24h → 72h → 168h**, with a **30-day rescue window** and **3 retry attempts**. These are configurable application defaults, not claims about any specific processor's exact production schedule.

## Architecture rule

The ML model predicts recoverability. The AI strategy layer recommends an action. The deterministic recovery playbook and policy engine decide whether that action is safe. Execution remains behind the existing authorization gate.
