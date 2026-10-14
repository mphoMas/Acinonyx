# Antigravity: GHA-02 whole-boundary correction

Base: ef6c5400, shared branch feat/scrum-board-automation. Read GHA_02_ARCHITECT_REVIEW.md. Implementation owner remains Antigravity; independent reviewer Codex. Existing V01–V07 criteria apply. No broader features or live activation.

## Before patching

Add reproductions for empty archive with supplied PASSED references; invalid model_copy/model_construct; original ZIP NUL; STORED header-size lie hiding excess data; and unauthenticated CLI DB initialization. Show each fails against this candidate. Prepare a short closure matrix across JSON/bytes/dict/model, archive-bytes/path, pure CLI and authenticated library publication. Fix the rule across routes, not only one example.

## Required correction

1. Always revalidate supported manifest inputs and all observation references. Treat zero observations as incomplete readiness claims when permitted; absent artifact bytes for supplied references are validation failures, never valid PASSED claims. Bound the complete serialized manifest consistently.
2. Validate original ZIP member names before library truncation. Reject unsafe/colliding names and nonregular metadata. Enforce compressed-input, member/count/actual decompression caps on the actual handle/stream. Reconcile supported local/central headers, STORED lengths and DEFLATE termination/unused data; reject header lies and hidden/trailing content without unbounded read/decompress. CRC/hash and actual byte length must cover the complete supported member.
3. Remove arbitrary live DB path and publication flags from the public offline CLI. Choose a pure offline snapshot/claims format, explicitly non-authoritative, or a trusted host-configured read-only fixture source. No PMDatabase initialization before authority. Keep mutation only in the authenticated SDK/service path, using current tenant binding and trusted repository configuration; no actor/admin flags, env-token improvisation or caller-selected production DB.
4. Do not accept a constructed valid ValidationResult as authority to bypass artifact/Git validation. Prefer one authenticated validate-and-submit operation owning original bounded inputs and fresh DB identity/CAS, with pure validation separately returning non-authoritative claims. It must reject altered input/result/payload and stale state. Never change the core service to admit unchecked artifacts.
5. Complete policy/intent/fence/brief/candidate/base/suite binding. Add bounded literal Git collection and safe input file reads. Use sys.executable for tests and honest structured errors; no candidate commands/hooks executed.
6. Correct delivery candidate, actual implementation description and coverage/runner receipts. Preserve readiness returns and formal rejections as distinct; report validator refusals separately rather than silently losing repeat work.

## Required adverse variants

- Empty ZIP+nonempty observations; all checks omitted; unknown/duplicate observation/reference; mismatched bytes/digest.
- Invalid JSON types/extra keys/duplicate keys/nonfinite values, malformed UTF8, oversized file input and constructed nested models.
- Original NUL names, traversal/absolute/backslash/control paths, duplicates, symlink/nonregular member, unsupported compression/encryption.
- Declared-size mismatch smaller/larger, STORED hidden bytes, DEFLATE hidden output/trailing/unterminated stream, CRC/truncation, total overflow and changed-file handle/race where applicable.
- Fresh real tenant binding: wrong actor, revoked session within binding, unbound/cross-tenant, stale CAS, altered run/fence/policy/base/suite, paused states.
- Unauthorized Git changes/rename ends/modes/links/submodules, missing commits, filenames treated as data; bounded timeout/output failure.
- Public CLI cannot select/init/migrate an operational DB or authorize publication. Pure mode never prints IN_REVIEW/ACCEPTED as an actual coordinator decision.
- Actual simultaneous publication race: one winner; rejected validation leaves rows, events, holds and schema unchanged.
- Clean installed wheel and isolated script execution outside the checkout, including failures and truthful output. Never substitute local import for wheel qualification.

Keep edits in the approved validator/script/tests and documentation scope. If a core defect requires changes elsewhere, reproduce and agree the interface before extending it. Do not edit IAM, migration, worker or signing authority merely to make tests pass.

Submit corrected code, closure matrix, actual targeted/full gate and installed-package results. Run the full gate on the final code; partial stage runs do not replace it. No self-acceptance, no GHA-03 dependency advancement.
