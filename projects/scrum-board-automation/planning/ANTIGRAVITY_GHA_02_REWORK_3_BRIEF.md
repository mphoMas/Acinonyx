# Antigravity — final bounded archive closure

Candidate `14408e20` closes the previous identity, FIFO and producer-side decompression findings. Preserve those fixes. Read `GHA_02_REWORK_3_REVIEW.md` for the remaining narrow defects.

1. Decide the supported ZIP profile. Prefer explicitly rejecting bit-3/data-descriptor and ZIP64 variants if these are unnecessary for the bounded artifact producer. If supporting descriptors, validate their CRC and sizes against measured data, support only documented signed/unsigned forms, and reject truncation or inconsistent local/central metadata. No unbounded reads or decompression may be introduced.
2. Add a regression: produce a DEFLATED member on an unseekable buffer, locate `PK\x07\x08`, overwrite its next three 32-bit fields with zero, and assert refusal. Test individual field corruption and valid supported formats. If rejecting the profile, include a valid ordinary seekable ZIP success case and explicit unsupported-profile failure cases.
3. Correct `GHA_02_DELIVERY.md`: the quality script stages are Ruff, doctor/capabilities, research link checks, compilation and full pytest. Report separately executed coordinator tests, Mypy if actually run, and wheel verification separately. Preserve exact counts/skips and distinguish author evidence from independent evidence.
4. Run targeted suites, final full gate and clean installed-wheel checks after the final code edit. Submit a new immutable candidate for independent review.

Scope remains validator/tests/documentation. No core delivery/schema changes, workflow activation, OIDC endpoint, provider dispatch or enrollment. GHA-03 stays gated. Do not self-mark accepted.
