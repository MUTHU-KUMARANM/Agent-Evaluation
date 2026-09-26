# Perturbation Log

## System 1: validated, routed pipeline

- **Change:** Used the existing controlled missing-source case: `endorsements` is null in a recorded tool response (test `test_ac_01_04_missing_source_halts_immediately`). No source policy file was modified.
- **Command:** `python -m pytest -q "Build a Validated, Routed Insurance Policy Extraction Pipeline\04-hitl-routing\solution\tests\test_us01_retry.py" -k missing_source_halts_immediately`
- **Prediction:** It will classify the missing source as futile to retry and escalate after one recorded call.
- **Actual:** `1 passed, 13 deselected`; the test asserts `RetryFutileEscalation`, `detected_pattern == "endorsements_absent"`, and `client.call_count == 1`. Full output: `01-policy-pipeline/perturbation-run.txt`.
- **Difference from baseline:** This is a focused deterministic test of the missing-source branch, not a live API perturbation or a changed policy document. Live routing is blocked by absent API credentials.

## System 2: schema-enforced two-pass extraction

- **Change:** Ran the provided `income_sum_mismatch.txt` discrepancy fixture, whose stated monthly total differs from the listed components by 1250.00.
- **Command:** `python -m mortgage_extractor fixtures/documents/income_sum_mismatch.txt --mode replay`
- **Prediction:** The extracted structure can be valid while independent arithmetic validation reports inconsistency.
- **Actual:** `consistent: false`; calculated 9642.17, stated 10892.17, delta -1250.00. Full output: `02-mortgage-extraction/discrepancy-run.txt`.
- **Difference from baseline:** Compared with the clean/unknown-field replay (`extract-run.txt`), this fixture produces a nonempty discrepancy list. It is a provided controlled edge-case fixture, not an edited copy of the source document.

## System 3: multi-source synthesis

- **Change intended:** The project rubric's `--simulate-timeout` source-failure mode.
- **Command attempted:** Supply Chain focused reader tests ran successfully; full suite collection recorded in `03-supply-chain/tests.txt`.
- **Prediction:** A timed-out source should be marked incomplete while independent source results permit a partial report.
- **Actual:** The full tests and CLI could not initialize because Windows Application Control blocked loading `grpc` (`03-supply-chain/tests.txt`). The focused reader suite reports `13 passed` (`03-supply-chain/reader-tests.txt`). No timeout run or briefing is claimed.
- **Difference from baseline:** No full baseline or timeout run was obtained. This rubric item remains unverified in this Windows environment.

