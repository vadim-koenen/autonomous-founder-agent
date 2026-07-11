# Cash Experiment Activation Handoff

Selected commercial path:

- Offer: Agent Launch QA Sprint
- Buyer: indie AI founders and small teams with a working build approaching launch
- Price: `$149` one-time
- Discovery: Contra service marketplace plus owner-published LinkedIn launch post
- Payment: Contra fixed-scope project or public guest-checkout link
- Fulfillment: agent-generated test matrix, report, repair patch, rerun, and handoff

## Why Contra

Contra combines the missing functions in one free starting account: a discoverable service, project terms, escrow or payment links, guest checkout, and fulfillment. Stripe solves payment but not discovery. Upwork has established purchase behavior but materially heavier catalog competition and proposal friction.

Official references:

- https://help.contra.com/en/articles/9322412-how-to-add-services-to-your-contra-profile
- https://help.contra.com/en/articles/9322763-paid-projects
- https://contra.com/features/payments

## Owner Setup

These actions require the owner's real identity and cannot be delegated to the autonomous operator:

1. Create or sign in to a Contra independent account.
2. Review and accept Contra's current legal terms.
3. Complete required identity, tax, bank, wallet, and payout setup directly with Contra.
4. Add the service using `offers/agent-launch-qa-sprint/LISTING.md`.
5. Upload `site/operator-social.png` as the service cover.
6. Set the one-time fixed price to `$149` and delivery to two days.
7. Publish the service and retain its public URL.
8. Create a fixed-scope project or guest-checkout payment link that preserves the published scope.
9. Provide only the public service and checkout URLs to the repository. Never provide credentials, tokens, tax records, bank details, private keys, or recovery phrases.

## Repository Activation

After owner setup, update `site/checkout-config.json`:

```json
{
  "status": "active",
  "experiment_id": "opp-agent-launch-qa",
  "provider": "contra",
  "checkout_url": "https://public-contra-checkout.example",
  "configured_by_human": true,
  "notes": "Public checkout URL only; no credentials."
}
```

The sales page will automatically replace every founding-intake button with the live checkout link.

## Manual Distribution

Publish `launch-copy/linkedin-agent-launch-qa.md` manually from the owner's real LinkedIn profile. Automated LinkedIn posting and messaging are intentionally disabled because LinkedIn's current rules prohibit third-party automation of posts, comments, and messages.

## First-Sale Verification

After Contra confirms a completed payment, record a public-safe transaction in `data/revenue_ledger.json` with a unique transaction ID, non-secret verification reference, verification timestamp, gross amount, fees, refunds, and direct costs. Do not include buyer identity.
