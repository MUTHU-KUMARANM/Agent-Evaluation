# Reflection Brief: Evaluation and Observability Capstone

**Date:** 2026-10-03

> The Linux evidence is from GitHub Actions run 37141918003, latest attempt 3. Offline runs use recorded responses. The live Anthropic request was rejected with HTTP 401 (`invalid x-api-key`); no extraction completed.

## 0. Environment

| Field | Value |
|---|---|
| Local environment | Windows 11, build 26200; Python 3.12.14 (earlier evidence in `environment.txt`). |
| Reproduction environment | GitHub Actions, Ubuntu 24.04.5 LTS; Python 3.12.14. |
| Date run | 2026-10-03 |
| Live model call | Attempted, but Anthropic rejected the configured key with HTTP 401 (`invalid x-api-key`); see `pipeline-run-live.txt`. |

## 1. Validated, routed pipeline

| Evidence | Value |
|---|---|
| Tests | 45 passed, 3 failed (`01-policy-pipeline/tests-full.txt`); the 3 live API tests failed authentication with HTTP 401. |
| End-to-end run / routing JSON | Not produced: the live call failed authentication; see `pipeline-run-live.txt`. |
| auto_approve / human_review / spot_check counts | Not available; there is no routing output to count. |

**1a. Retry boundary.** The controlled recorded-response test in `perturbation-run.txt` passes: null `endorsements` is classified as `endorsements_absent` and the test asserts exactly one client call. Retrying cannot recover information absent from the source; it wastes calls and risks fabrication instead of escalation.

**1b. Reading the router.** Still unverified. Without the live pipeline output and `routing_decisions.json`, I cannot identify a real human-review record or its driving signal.

**1c. Where the aggregate lies.** In `calibration-report.txt`, `umbrella × exclusions` has confidence 0.93, accuracy 0.00, n=2, and Brier 0.865, while overall Brier is 0.291. The slice exposes a weak area concealed by the aggregate; the two-example sample is too small for a stable population estimate.

## 2. Schema-enforced two-pass extraction

| Evidence | Value |
|---|---|
| Passing tests | 25 passed (`02-mortgage-extraction/tests-full.txt`). |
| Document run | `income_missing_bonus.txt`; replay output is `extract-run.txt`. |
| Classified type | Income/paystub extraction, inferred from the returned income fields; the CLI output itself does not emit a type label. |

**2a. Two guarantees.** `discrepancy-run.txt` shows calculated monthly income 9642.17, stated 10892.17, delta -1250.00, and `consistent: false`. Schema/tool enforcement checks structure and types; the independent validator checks arithmetic. Neither proves the source document is authentic or that every value was read correctly.

**2b. Refusing to fabricate.** In `extract-run.txt`, absent `bonus_monthly` and `bonus_ytd` are null. Nullable optional fields preserve “not stated” as distinct from explicit zero.

**2c. Normalization.** The appraisal fixture says “approximately 2,400 sq ft”; `normalization-run.txt` returns `gross_living_area_sqft: 2400`. Normalizing at extraction gives downstream comparisons a stable numeric value.

## 3. Multi-source synthesis

| Evidence | Value |
|---|---|
| Passing tests | 34 passed (`03-supply-chain/tests-full.txt`). |
| Investigation / briefing | `investigation-run.txt` and `briefing.txt`; sections include Well-Established, Contested, and Incomplete. |
| Timeout run | `timeout-run.txt`; command exited 0. |

**3a. Annotate, don't arbitrate.** In the Contested section of `briefing.txt`, on-time delivery is 95.0% from `supplier_audit` (2026-04-10) and 78.0% from `logistics` (2026-04-05). Retaining both with source and date lets a reviewer see a possible reporting-window difference instead of treating one value as ground truth.

**3b. Source goes dark.** `timeout-run.txt` reports “Sources unavailable: logistics unavailable (timeout)” and the Incomplete section marks `late_shipment_count` as “missing source: timeout reading logistics.” The run exits 0 and still includes available-source results. A timeout is an explicit coverage gap, not evidence that there was nothing to report.

**3c. Dates as a guardrail.** The same on-time-delivery metric is 95.0% from supplier audit (2026-04-10) and 78.0% from logistics (2026-04-05), both in `briefing.txt`. Dates expose that these are differently dated observations, so readers can investigate differing windows rather than read them as a timeless contradiction.

## 4. Synthesis

**4a. One principle.** Keep evidence distinctions visible. Mortgage arithmetic validation catches a mismatch after schema extraction; the policy unit tests separate missing-source escalation from retryable errors; and Supply Chain preserves source/date attribution while marking timed-out coverage Incomplete.

**4b. Confidence is not correctness.** The mortgage discrepancy is the clearest observed catch: well-formed extracted fields still failed the independent sum check. Supply Chain reinforces the same lesson in a different way: two differently dated delivery-rate values remain contested rather than being collapsed into a falsely precise number.

**4c. Apply it.** For supplier-invoice processing, I would extract typed fields, deterministically reconcile totals to line items and purchase orders, independently route mismatches for review, and preserve source/date metadata while marking missing sources explicitly. I would monitor schema failures, discrepancy and null rates by field, reviewer overrides, source timeouts, and per-source freshness.

## Remaining blocker

The Linux suites and Supply Chain investigation/timeout now run successfully. The policy live pipeline and routing evidence remain incomplete: the workflow received a masked key, but Anthropic rejected it with HTTP 401 (`invalid x-api-key`). Replace the repository secret with a valid Anthropic API key and rerun the workflow. No key value is included in logs or this repository.
