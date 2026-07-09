# Payment Activation

M2 keeps checkout pending until a human provides a public checkout URL.

Do not put API keys, webhook secrets, private keys, seed phrases, bank data, tax data, or account credentials in this repository.

## Recommended Path: Lemon Squeezy

1. Create or log in to a Lemon Squeezy account.
2. Complete required store, payout, tax, and identity setup inside Lemon Squeezy.
3. Create a product named `Agent-to-Agent Commerce Starter Kit`.
4. Set price to `$19` one-time.
5. Upload the paid bundle files from `starter-kit/paid-bundle/`.
6. Add product description from `starter-kit/paid-bundle/storefront-listing.md`.
7. Confirm refund/support language is acceptable.
8. Copy the public checkout URL.
9. Provide only the public checkout URL for wiring into the site.

## Alternate Path: Stripe Payment Link

1. Create or log in to a Stripe account.
2. Complete required business, payout, tax, and identity setup inside Stripe.
3. Create a product named `Agent-to-Agent Commerce Starter Kit`.
4. Set price to `$19` one-time.
5. Create a Payment Link for that product.
6. Configure post-payment delivery manually or through a separate approved delivery process.
7. Copy the public Payment Link URL.
8. Provide only the public checkout URL for wiring into the site.

## Site Wiring

After a public checkout URL exists, update `site/checkout-config.json`:

```json
{
  "status": "active",
  "provider": "lemon_squeezy",
  "checkout_url": "https://public-checkout-url.example",
  "configured_by_human": true
}
```

Allowed providers:

- `lemon_squeezy`
- `stripe_payment_link`

Then update `AGENT_MANIFEST.json` so `commerce_channels.human_checkout.checkout_url` matches the public URL.

## Revenue Tracking

Revenue source of truth remains the payment provider dashboard until an API integration is explicitly approved.

Manual ledger update after first sale:

1. Confirm sale in Lemon Squeezy or Stripe dashboard.
2. Record sale date, gross revenue, fees, net revenue, provider, and order/reference ID in `docs/REVENUE_LEDGER.md`.
3. Do not record buyer personal data in the public repository.
4. Update physical-form fund totals.

## Wallet / Agent-Native Payment Setup Later

Do not create or connect wallet payment rails in M2 unless a separate wallet activation plan is approved.

If wallet activation is later approved:

1. Create a dedicated project wallet, separate from personal wallets.
2. Store recovery phrase offline; never paste it into chat, code, docs, environment files, screenshots, or issues.
3. Start with testnet only.
4. Set transaction limits.
5. Require human approval for every mainnet transaction.
6. Document the exact agent-native payment rail before activating it.

## Current Status

Checkout status: pending

Reason: no public Lemon Squeezy or Stripe checkout URL has been provided yet.
