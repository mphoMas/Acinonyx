# 📦 EVIDENCE BUNDLE: FINOPS PILOT (BRIEF B) & HARDENED RELEASE POLICY
**Authority:** Office of the Chief Principal Agentic Engineer & Architect
**Package Version:** v2.0 (Post-Bounded Review Hardened)
**Runtime:** Linux 7.0.0-38-generic x86_64 | Python 3.14.6 | Pytest 9.0.3 | Playwright 1.63.0 (Chrome 140)

---

## 1. Verified Cryptographic Hashes (SHA-256) of Packaged Files

| Relative Path | Size (Bytes) | SHA-256 Hash | Verification Role |
|:---|:---|:---|:---|
| `DEPENDENCY_VERSIONS.txt` | 252 B | `0f36d5d2e3cf021d49774ea61cd84eb634baa72ad0d82200d7ef34d908321b9a` | Verified Packaged Artifact |
| `INDEPENDENT_POLICY_SPEC.json` | 738 B | `1764d7ac529c3056db3538b89acaf51d091cb6c3986103c9b8b3a6f6dcf1a667` | Verified Packaged Artifact |
| `RAW_VERIFICATION_OUTPUTS.txt` | 3813 B | `af33cf55c52721819efb7c26475342a7c7c28ab58329f9998d714086abe54797` | Verified Packaged Artifact |
| `mas/release_policy.py` | 13557 B | `6a6353e8056c743b28fd6267ab51bf1de3b56d80a84dfd2491df8c6cc4bfa3ef` | Verified Packaged Artifact |
| `mas/validation.py` | 5858 B | `dea19c1a0d3a81d9a1a70a3ac16a514736a64a741ae7efc80b327217abf462d5` | Verified Packaged Artifact |
| `tests/test_deliberately_broken_candidate.py` | 11667 B | `fc9a4f7bcc483a2a0845fe030cafefb96251b4aedbeea5d349116ac2ae81f030` | Verified Packaged Artifact |
| `tests/test_release_policy.py` | 20345 B | `7cd355fcc0536074541623a2973e410225d20bf0ac0c1d8b246793306e3c403d` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/candidate_0.html` | 2753 B | `3056aa5ee260d9f4cd437aaedf038022f8d2a66510a565d5cba68b6a3d765bf9` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/candidate_0_desktop.png` | 33489 B | `a79e4064cd1dfecab68a911489053fba4d2c583903ded7b09b48227d860ce01a` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/candidate_1.html` | 5003 B | `09e50480ff9fc5d326a4524dc24fe31a0972bdf1c09d3d20528e90721ee258e1` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/candidate_1_desktop.png` | 34492 B | `7cc2e32b5873f6e162507293bc35333fde961196099b0c88c1b33a12810ab523` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/candidate_1_rebalanced.png` | 42427 B | `ca2bb35a73b6321e75dff23feacf65c4016492d797964e06d270ae5b0fa2d883` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/evidence/candidate_0_contrast_trace.json` | 483 B | `2706940ac16e9f5ea07ce97c2cc9661ee297761ad1d8f166e6c65f86e1536681` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/evidence/candidate_0_target_size_trace.json` | 629 B | `8bd38c1be0f19b29f3b5f164a0db24e09ac8371f5b1e87ba73b60087f7e4a71b` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/fact_sheet_finops_v1.0.json` | 1719 B | `f839e8a855f9814975b1cb14515cbee35b08fde6b129a1a04bb6420ed1815ddc` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/pilot_execution_report.json` | 3384 B | `fd84337d2edeff83c4e8a765ec36067e2bda594b82c95b32e53a28a33442c1b3` | Verified Packaged Artifact |
| `workspace/pilot_brief_b/run_pilot.py` | 14459 B | `10321cabb1e9c36326c6e0385102969f130ee89e7f8abad5fdb418b9ec064f52` | Verified Packaged Artifact |

---

## 2. Hardened Architecture & Key Defect Fixes

1. **Dynamic Candidate DOM Inspection:** `run_pilot.py` dynamically extracts actual CSS styles, parent card backgrounds, contrast ratios, claim bindings, and JavaScript handlers. Zero hardcoded findings.
2. **Rejection of Deliberately Broken Candidate:** Automated test `tests/test_deliberately_broken_candidate.py` strips `<script>` and sets button foreground equal to background. The harness dynamically detects contrast ratio 1.0:1 and missing action script, returning `RELEASE_BLOCKED`.
3. **Strict Evaluator Input Hardening:** Blocks non-hex hashes, missing `findings` lists, non-boolean `execution_complete` (e.g. `"false"`), and null `suite_executions` without crashing.
4. **Non-Blocking Style Advisories:** Advisory findings never block release, strictly preserving separation between functional correctness and stylistic suggestions.
5. **Independent Policy Loading:** Loads `INDEPENDENT_POLICY_SPEC.json` directly from file.
6. **Accurate Card Background Contrast:** Computes button contrast against actual container card `#141310` (effective ratio 2.5039:1 in Candidate 0).
7. **Consistent Fact Metric:** Reconciled fact sheet and UI to aggregate spend ($184,210 reduced to $169,210).

---

## 3. Reproduction Instructions

```bash
# 1. Run all 16 release policy and deliberate-break unit tests
python3 -m pytest tests/test_release_policy.py tests/test_deliberately_broken_candidate.py -v

# 2. Run the dynamic pilot verification harness
python3 workspace/pilot_brief_b/run_pilot.py

# 3. Check hashes against manifest
sha256sum mas/release_policy.py tests/* workspace/pilot_brief_b/*
```
