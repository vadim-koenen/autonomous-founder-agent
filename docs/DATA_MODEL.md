# Autonomous Revenue Operator Data Model

M3 models are defined in `founder_agent/operator_models.py`. Historical M1 models remain in `founder_agent/models.py`.

## Evidence Record

Every external signal includes:

- `evidence_id`
- `title`
- `source_url`
- `observed_at`
- `summary`
- `quality`
- structured `signals`
- `caveats`

An opportunity cannot enter a cycle if it references an evidence ID absent from the scan.

## Opportunity

An opportunity is a current revenue hypothesis, not an active business identity.

It records:

- ID, name, category, thesis, offer, buyer, and price
- acquisition channel and proposed payment rail
- estimated cost and expected outcome
- required human actions and available agent actions
- evidence IDs and free substitutes
- scores for all 17 decision criteria
- cash, asset, and frontier role fit
- required assets and next executable action
- channel and authority for the next action
- required human setup
- 72-hour validation, kill, pivot, and scale criteria

## Experiment

An experiment is a selected opportunity with operating state.

Required fields:

- `experiment_id`
- `opportunity_id`
- `role`
- `thesis`
- `offer`
- `intended_buyer`
- `price`
- `acquisition_channel`
- `payment_rail`
- `estimated_cost`
- `actual_cost`
- `expected_outcome`
- `actual_impressions`
- `actual_contacts`
- `actual_replies`
- `actual_checkout_starts`
- `actual_purchases`
- `gross_revenue`
- `fees`
- `refunds`
- `net_revenue`
- `human_actions_required`
- `agent_actions_available`
- `evidence`
- `start_date`
- `review_date`
- `kill_criteria`
- `pivot_criteria`
- `scale_criteria`
- `current_status`
- required assets, next action, channel, authority, setup, validation, and last decision

Statuses are `proposed`, `building`, `validating`, `active`, `scaling`, `pivoted`, `killed`, `completed`, or `blocked`.

## Channel Record

Each channel in `data/channel_registry.json` separates capability from access:

- ID and name
- discovery, distribution, marketplace, human payment, agent-native payment, publishing, or fulfillment kinds
- whether an account exists
- whether human verification is required
- whether the agent has access
- authority class
- permitted actions
- costs
- platform restrictions
- current status
- source URL and last-check date

## Action Decision

An action records:

- action and experiment IDs
- description
- authority class
- channel ID
- whether it is executable now
- a blocked reason when it is not executable

This record is a decision, not proof that the external action occurred.

## Transaction Record

Each ledger entry contains:

- transaction and experiment IDs
- occurrence date and status
- verification reference and timestamp
- currency and gross amount
- processor fees
- platform fees
- refunds
- direct costs
- public-safe notes

Buyer names, email addresses, credentials, and private fulfillment data do not belong in the public ledger.

## Revenue Summary

The derived summary contains verified transaction count, gross, processor fees, platform fees, refunds, direct costs, net revenue, physical-form fund, reinvestment balance, and contingency reserve.

## Public Operator State

`data/operator_state.json` contains the current cycle ID, date, mission, active portfolio, full opportunity ranking, verified revenue summary, executable actions, blocked actions, recent lifecycle history, decisions, evidence IDs, owner spend, capital policy, and caveats.
