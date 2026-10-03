# Perturbation Log

## System 1: validated, routed pipeline

- **Controlled edge case:** Used the recorded tool response in `test_ac_01_04_missing_source_halts_immediately` with required `endorsements: null`.
- **Command:** `python -m pytest -q tests/test_us01_retry.py -k missing_source_halts_immediately` (from the final policy solution directory).
- **Prediction:** The system treats absent source evidence as futile to retry and escalates after one model-client call.
- **Observed:** The test passed; it asserts `RetryFutileEscalation`, pattern `endorsements_absent`, and one client call. See `01-policy-pipeline/perturbation-run.txt`.
- **Compared with ordinary input:** A complete recorded response can proceed through extraction; the null-required-field response instead escalates. This is a deterministic recorded test, not a live API run or modified source policy. The end-to-end routing run remains blocked because the workflow received no API key.

## System 2: schema-enforced two-pass extraction

- **Input variation:** Selected the provided `income_sum_mismatch.txt` edge-case fixture, where the stated monthly total differs from the line-item sum by 1250.00.
- **Command:** `python -m mortgage_extractor fixtures/documents/income_sum_mismatch.txt --mode replay`.
- **Prediction:** Extraction remains structurally valid, but independent arithmetic validation flags the mismatch.
- **Observed:** `consistent: false`; calculated 9642.17, stated 10892.17, delta -1250.00. See `02-mortgage-extraction/discrepancy-run.txt`.
- **Compared with ordinary input:** The missing-bonus replay returns a consistent result with nullable fields, while this mismatch fixture returns a nonempty discrepancy list.

## System 3: multi-source synthesis

- **Configuration change:** Enabled `--simulate-timeout` for the logistics reader while keeping recorded news extraction offline.
- **Command:** `supply-chain-investigate meridian --offline --simulate-timeout`.
- **Prediction:** Logistics is reported unavailable, the briefing marks its missing exclusive metric Incomplete, and available sources still produce a briefing.
- **Observed:** `timeout-run.txt` says “Sources unavailable: logistics unavailable (timeout)” and lists `late_shipment_count` as “missing source: timeout reading logistics”; exit code 0.
- **Compared with ordinary input:** `investigation-run.txt` includes logistics claims and reports an on-time-delivery conflict (95.0% supplier audit vs. 78.0% logistics). The timeout run omits the unavailable logistics values, identifies the gap, and completes.
