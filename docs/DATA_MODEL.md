# Revenue Strategy Data Model

The M1 model is defined in `founder_agent/models.py`.

## `RevenueStrategy`

A candidate revenue path considered by the agent.

Fields:

- `strategy_id`: stable identifier such as `afa-001`
- `name`: human-readable strategy name
- `category`: broad opportunity category
- `thesis`: why this could make money
- `target_buyer`: first likely buyer segment
- `first_offer`: smallest sellable offer
- `distribution_channels`: possible channels after approval
- `agent_build_assets`: assets the agent can create locally
- `research_notes`: notes about timing, buyer need, or risk
- `external_actions_required`: launch actions that are not executed in M1
- `dimension_scores`: 1-10 score for every rubric dimension
- `score_notes`: concise explanation of the strategy's score
- `not_user_business_bound`: default `true`; the strategy is not assumed to be KRS or any existing user business

## `ScoredStrategy`

The result of applying the rubric to one strategy.

Fields:

- `strategy`
- `weighted_score`
- `raw_score_total`
- `dimension_scores`
- `dimension_weights`

## `LaunchPlan`

The concrete plan for the selected experiment.

Fields:

- `strategy_id`
- `experiment_name`
- `objective`
- `price_test`
- `draft_assets_to_build`
- `internal_build_steps`
- `validation_steps_before_launch`
- `external_actions_required`
- `approval_checklist`
- `stop_conditions`
- `reinvestment_path`
- `m1_boundary_statement`

## `ExternalActionRequest`

A launch action that can be planned but not executed in M1.

Fields:

- `action_type`
- `description`
- `approval_required`: always `true` for M1 launch actions
- `performed`: always `false` for M1 generated plans

## Rubric Dimensions

Every candidate is scored 1-10 on:

- speed to first dollar
- startup cost efficiency
- probability of first sale
- gross margin
- distribution leverage
- novelty/attention potential
- automation leverage
- current market timing
- scalability
- reinvestment potential
- platform risk, reverse scored
- legal/compliance risk, reverse scored

Reverse-scored risk means a high score is good: `10` means low risk, `1` means high risk.
