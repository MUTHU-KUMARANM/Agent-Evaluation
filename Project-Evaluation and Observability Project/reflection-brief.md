# Reflection Brief: Evaluation and Observability Capstone

**Date:** 2026-09-26

> Evidence below is from deterministic recorded-response tests and offline runs. A live Anthropic
> request was not completed because this environment has no `ANTHROPIC_API_KEY`.

## 0. Environment

| Field | Value |
|---|---|
| OS & version | Windows 11, build 26200 (Microsoft Windows NT 10.0.26200.0) |
| Python version | 3.12.14 |
| Date run | 2026-09-26 |
| Ran any system live? | No live Anthropic requests; mortgage replay used recorded responses. |

## 1. Validated, routed pipeline

| Evidence | Value |
|---|---|
| Passing test count | 45 passed, 3 skipped (`01-policy-pipeline/tests.txt`) |
| Routing output file | Not generated: live pipeline stopped at missing Anthropic credentials (`pipeline-run.txt`). |
| auto_approve / human_review / spot_check | Not available; no routing output was produced. |

**1a. Retry boundary.** The missing-source unit test passes (`01-policy-pipeline/perturbation-run.txt`): a null `endorsements` value is classified `endorsements_absent` and the recorded client is called exactly once. Retrying cannot recover information absent from the source; it adds cost and may encourage fabrication instead of escalating.

**1b. Reading the router.** Not answerable from this run: no routing JSON exists because the Anthropic client failed authentication before processing policies. No human-review record is claimed.

**1c. Where the aggregate lies.** `umbrella × exclusions` has confidence 0.93 and accuracy 0.00 (n=2, Brier 0.865); overall Brier is 0.291 (`calibration-report.txt`). Slicing reveals a poorly calibrated field/policy combination that an aggregate can conceal. The sample is small, so this is a warning, not a stable population estimate.

## 2. Schema-enforced two-pass extraction

| Evidence | Value |
|---|---|
| Passing test count | 25 passed (`02-mortgage-extraction/tests.txt`) |
| Document run | `fixtures/documents/income_missing_bonus.txt` in `extract-run.txt`; normalization run is in `normalization-run.txt`. |
| Classified type | Paystub/income document (inferred from extracted income fields and fixture name; the CLI JSON does not emit a document-type label). |

**2a. Two guarantees.** In `discrepancy-run.txt`, calculated monthly income is 9642.17, stated is 10892.17, delta -1250.00, and `consistent` is false. Structured tool/schema validation guarantees shape and types, not arithmetic truth; the independent validator checks the sum, but cannot prove that the source document itself is authentic or correctly read.

**2b. Refusing to fabricate.** `extract-run.txt` contains `bonus_monthly: null` and `bonus_ytd: null` when absent, while validation remains consistent. Nullable optional schema fields represent unknown/unstated values separately from explicit zero; inventing a bonus would misstate evidence.

**2c. Normalization.** Fixture `appraisal_informal_sqft.txt` says “approximately 2,400 sq ft”; `normalization-run.txt` emits `gross_living_area_sqft: 2400`. Normalizing once at the extraction boundary gives downstream validation and comparison a stable numeric value.

## 3. Multi-source synthesis

| Evidence | Value |
|---|---|
| Full-suite passing test count | Not established: collection is blocked by Windows Application Control denying the `grpc` extension load (`03-supply-chain/tests.txt`). |
| Focused reader tests | 13 passed (`03-supply-chain/reader-tests.txt`). |
| Briefing file / conflict section | Not generated; CLI/evaluation could not be run through the blocked dependency. |

**3a. Annotate, don't arbitrate.** No briefing was produced, so there is no observed conflicting-metric pair to quote.

**3b. Source goes dark.** A full `--simulate-timeout` run and its briefing are unavailable for the same `grpc` load block. The intended behavior is specified by the project, but is not represented as verified evidence here.

**3c. Dates as a guardrail.** No dated supplier claims were generated in this run; I cannot quote an observed pair.

## 4. Synthesis

**4a. One principle.** The mortgage replay discrepancy is the clearest observed check: syntactically structured values were independently summed and flagged (`discrepancy-run.txt`).

**4b. Confidence is not correctness.** Mortgage validation mattered most in the captured runs because it detected a 1250.00 inconsistency despite a well-formed extraction. The policy calibration slice also shows confidence 0.93 alongside accuracy 0.00 on two examples, but that sample is very small.

**4c. Apply it.** For supplier invoice intake, I would start with schema-constrained extraction plus deterministic reconciliation of invoice totals, quantities, and purchase-order values, then route mismatches to a person. I would instrument schema failures, per-field discrepancy rates, null rates, reviewer overrides, latency, and source-level timeout rates.

## Run limitations

The live Anthropic pipeline did not run: no API credential was configured, and no key was supplied. The Supply Chain full test collection/CLI did not run because Windows Application Control denied loading `grpc`; the focused reader tests do pass. The missing live routing, synthesis, and timeout evidence means this submission is not yet fully verified against every rubric item.

