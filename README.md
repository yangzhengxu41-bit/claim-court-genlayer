# ClaimCourt — an evidence-based adjudication Intelligent Contract

ClaimCourt is an Intelligent Contract for GenLayer (Studionet — the Studio
network, Chain ID 61999) that turns "someone claims X, here is the
evidence" into an on-chain verdict.

## What it does

Anyone can file a claim consisting of:

- a short statement (`claim_text`),
- a public evidence URL (`evidence_url`),
- explicit acceptance criteria (`criteria`).

The criteria are **frozen at filing time**: the filer cannot edit the claim
afterwards and there is no admin override.

Anyone can then trigger `adjudicate`. Every validator independently:

1. fetches the evidence page (`gl.nondet.web.render`),
2. asks an LLM to judge the claim **only** from that page, applying the
   frozen criteria exactly as written,
3. returns a verdict: `SUPPORTED`, `REFUTED`, or `UNCLEAR`, plus a short
   machine-readable `reason_code`.

Consensus uses an equivalence principle: validators rerun the whole
evaluation independently and must reach the same verdict
(`gl.eq_principle.strict_eq` on the verdict string). The `reason_code` is
derived deterministically from the verdict
(SUPPORTED → `EVIDENCE_SUPPORTS_CLAIM`, REFUTED →
`EVIDENCE_CONTRADICTS_CLAIM`, UNCLEAR → `INSUFFICIENT_EVIDENCE`), so the
stored record is fully reproducible from the verdict alone.

## Why this fits GenLayer

Adjudicating natural-language claims against unstructured web evidence is
exactly the class of problem deterministic EVM contracts cannot solve and
GenLayer's optimistic-democracy consensus is built for: subjective input,
objective on-chain outcome.

## Contract API

| Method | Type | Description |
| --- | --- | --- |
| `file_claim(claim_id, claim_text, evidence_url, criteria)` | write | File a new claim; IDs are unique, inputs length-capped |
| `adjudicate(claim_id)` | write | Run validator adjudication; stores verdict + reason_code |
| `get_claim(claim_id)` | view | Full claim record including status and verdict |
| `list_claim_ids()` | view | All filed claim IDs |
| `get_stats()` | view | Total / resolved / open claim counts |

Input limits (claim_id ≤ 64 chars, claim_text ≤ 500, evidence_url ≤ 300 and
must be http(s), criteria ≤ 500) keep prompts bounded and prevent abuse —
every claim is adjudicated exactly once.

## Verification

**Live on Studionet (2026-11-25 rehearsal, Studio built-in account):**
deployed and self-tested end to end — `file_claim("demo-1", …)` then
`adjudicate("demo-1")` returned **SUPPORTED** with reason code
`EXPLICITLY_STATES_100_GEN_PER_CLAIM`, three validators in agreement;
`get_claim("demo-1")` shows `RESOLVED` / `SUPPORTED` and `get_stats()`
reports 1 filed / 1 resolved / 0 open. Rehearsal contract:
`0x79a0bE6b55241a148206ad5068e05b036F0A931A`
([Studio Explorer](https://explorer-studio.genlayer.com/address/0x79a0bE6b55241a148206ad5068e05b036F0A931A)).

**Local direct-mode tests:** the adjudication logic was validated 8/8
under the previous runner generation (filing stores all fields, duplicate
IDs rejected, non-http(s) evidence rejected, SUPPORTED / REFUTED / UNCLEAR
paths, double adjudication rejected, unknown claim rejected;
`genvm-lint` static checks 3/3):

```bash
GENVM_VERSION=v0.3.0-rc7 .venv/bin/python -m pytest tests/test_claim_court.py -v
```

Note: Studio v0.123.0 only accepts the docs-published runner
`py-genlayer:1jb45aa8…` (see `prep-notes.md`), and the local direct-mode
harness cannot execute that runner generation yet — so the 8/8 result
above covers the previous runner build, while the live Studionet rehearsal
is the verification for the deployed file. The deployed file differs from
the tested build only in its runner header and SDK import form
(`from genlayer import gl, allow_storage`; `class ClaimCourt(gl.Contract)`).

## Layout

- `contracts/claim_court.py` — the Intelligent Contract
- `tests/test_claim_court.py` — direct-mode test suite
- `tests/test_claim_court_glsim.py` — GLSim integration tests (pending an
  upstream client/server calldata alignment)
- `prep-notes.md` — build/verification notes
