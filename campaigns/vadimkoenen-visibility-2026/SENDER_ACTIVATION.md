# Sender Activation Runbook

## Current verified state — 2026-07-26

- `vadimkoenen.net` receives mail through Cloudflare Email Routing.
- Its public SPF authorizes Cloudflare routing and HubSpot marketing mail.
- DMARC is monitoring-only (`p=none`).
- Public Cloudflare-routing and HubSpot-marketing DKIM records do not prove that
  a message sent through Apollo will authenticate.
- Apollo Free has no linked domain and shows one partially configured mailbox:
  an unrelated Gmail account.
- The requested `.net` sender address is not the linked Apollo mailbox.
- Five reviewed pilot contacts are saved in Apollo and 95 credits remain; no
  sequence, enrollment, approval, or send exists.

Therefore the current safe commercial-send volume is **zero**.

## Sender decision

Use the requested `.net` address only if it is a real outbound mailbox with working
reply synchronization and aligned authentication. A forwarding alias is not
enough.

If the `.net` address cannot be made into an authenticated mailbox, prefer a
real mailbox on `vadimkoenen.com` so the sender and website share a brand domain.
Do not create a throwaway outreach domain for this pilot.

## Owner-controlled setup

1. Choose the real outbound provider and mailbox.
2. Link that exact mailbox to Apollo through its supported Google or Microsoft
   flow; do not use an unrelated Gmail mailbox as a hidden alias.
3. Publish the provider's SPF and DKIM records without creating multiple SPF
   records.
4. Send one plain-text test to an independent mailbox and retain the full
   headers.
5. Confirm `Authentication-Results` shows SPF pass, DKIM pass with an aligned
   `d=` domain, and DMARC pass for the exact visible From address.
6. Confirm replies synchronize back to the linked mailbox.
7. Configure the truthful sender name, company/site identity, and a valid
   physical postal address.
8. Verify Apollo's unsubscribe link in every step and process reply-based
   opt-outs.
9. Enable rules that stop on reply, unsubscribe, or bounce.
10. Create the sequence inactive and keep every enrolled contact paused.

Do not place mailbox passwords, API keys, message headers containing private
recipient data, or DNS-provider credentials in the repository.

## Initial limits after verification

- Five reviewed first touches per weekday.
- No more than two messages per hour.
- At least ten minutes between sends.
- One person per company.
- Increase to ten per weekday only after five healthy business days.
- Pause immediately on any complaint, authentication failure, suppression
  failure, or hard-bounce rate above 2%.

Use meaningful replies, systems-review requests, and verified transactions for
decisions. Do not use open rate.

## Evidence required by the preflight

- Exact linked From mailbox.
- Redacted test-message authentication result.
- Apollo mailbox/domain setup state.
- Physical-address and sender-identity verification.
- Rendered unsubscribe evidence.
- Stop-rule configuration evidence.
- Current CRM-contact suppression snapshot.
- Current CRM customer/opportunity snapshot, including an authoritative
  zero-record snapshot when none exist.
- Current Apollo unsubscribe, bounce, and DNC snapshot, including an
  authoritative zero-record snapshot when none exist.
- Enabled central commercial-email capability grant with a positive per-cycle
  ceiling.

Reference:

- [Apollo mailbox linking](https://knowledge.apollo.io/hc/en-us/articles/4409127806093-Link-Your-Mailbox-to-Apollo)
- [Apollo sending limits](https://knowledge.apollo.io/hc/en-us/articles/4409233349005-Configure-Email-Sending-Limits)
- [Apollo unsubscribe configuration](https://knowledge.apollo.io/hc/en-us/articles/4409140379661-Configure-Your-Email-Unsubscribe-Link)
- [Apollo sequence rules](https://knowledge.apollo.io/hc/en-us/articles/4409396858509-Manage-Sequence-Rulesets)
- [Google sender requirements](https://support.google.com/mail/answer/81126)
- [FTC CAN-SPAM compliance guide](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)
