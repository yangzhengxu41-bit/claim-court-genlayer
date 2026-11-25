# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass

from genlayer import gl, allow_storage


@allow_storage
@dataclass
class Claim:
    claim_id: str
    claimant: str
    claim_text: str
    evidence_url: str
    criteria: str
    status: str  # "OPEN" | "RESOLVED"
    verdict: str  # "" | "SUPPORTED" | "REFUTED" | "UNCLEAR"
    reason_code: str


class ClaimCourt(gl.Contract):
    """Evidence-based claim adjudication court.

    Anyone can file a claim: a statement plus a public evidence URL plus
    explicit acceptance criteria. Anyone can then trigger adjudication:
    every validator independently fetches the evidence page, asks an LLM
    to judge the claim against the criteria frozen at filing time, and
    the network records the verdict under this court's equivalence
    principle: validators rerun the evaluation independently and must
    reach the same verdict (the reason_code wording may differ). The filer cannot edit the claim
    afterwards and there is no admin override: the outcome is whatever
    the evidence supports under validator consensus.
    """

    claims: gl.storage.TreeMap[str, Claim]
    claim_count: gl.u256
    resolved_count: gl.u256

    def __init__(self) -> None:
        self.claim_count = gl.u256(0)
        self.resolved_count = gl.u256(0)

    @gl.public.write
    def file_claim(
        self,
        claim_id: str,
        claim_text: str,
        evidence_url: str,
        criteria: str,
    ) -> str:
        if len(claim_id) == 0 or len(claim_id) > 64:
            raise gl.vm.UserError("claim_id must be 1..64 characters")
        if claim_id in self.claims:
            raise gl.vm.UserError("claim id already exists")
        if len(claim_text) == 0 or len(claim_text) > 500:
            raise gl.vm.UserError("claim_text must be 1..500 characters")
        if not (
            evidence_url.startswith("https://")
            or evidence_url.startswith("http://")
        ):
            raise gl.vm.UserError("evidence_url must be an http(s) URL")
        if len(evidence_url) > 300:
            raise gl.vm.UserError("evidence_url too long")
        if len(criteria) == 0 or len(criteria) > 500:
            raise gl.vm.UserError("criteria must be 1..500 characters")

        self.claims[claim_id] = Claim(
            claim_id=claim_id,
            claimant=str(gl.message.sender_address),
            claim_text=claim_text,
            evidence_url=evidence_url,
            criteria=criteria,
            status="OPEN",
            verdict="",
            reason_code="",
        )
        self.claim_count = gl.u256(int(self.claim_count) + 1)
        return claim_id

    @gl.public.write
    def adjudicate(self, claim_id: str) -> str:
        if claim_id not in self.claims:
            raise gl.vm.UserError("unknown claim id")
        claim = self.claims[claim_id]
        if claim.status != "OPEN":
            raise gl.vm.UserError("claim already adjudicated")

        claim_text = claim.claim_text
        evidence_url = claim.evidence_url
        criteria = claim.criteria

        def evaluate() -> str:
            page = gl.nondet.web.render(evidence_url, mode="text")
            task = f"""ClaimCourt adjudication review.

You are an impartial adjudicator for an on-chain claim court.
Judge the claim ONLY from the evidence page content below, applying
the acceptance criteria exactly as written. Do not use outside
knowledge and do not guess facts that are not on the page.

CLAIM:
{claim_text}

ACCEPTANCE CRITERIA:
{criteria}

EVIDENCE PAGE CONTENT:
{page[:4000]}

Reply with a JSON object and nothing else:
{{"verdict": "SUPPORTED" | "REFUTED" | "UNCLEAR", "reason_code": "SHORT_UPPER_SNAKE_CODE"}}
Use SUPPORTED when the evidence clearly satisfies the criteria,
REFUTED when the evidence clearly contradicts the claim or shows the
criteria are not met, and UNCLEAR when the page does not contain
enough information to decide.
"""
            raw = gl.nondet.exec_prompt(task, response_format="json")
            if isinstance(raw, str):
                raw = json.loads(raw)
            verdict = str(raw.get("verdict", "UNCLEAR")).strip().upper()
            reason = str(raw.get("reason_code", "NO_REASON_GIVEN")).strip()
            if verdict not in ("SUPPORTED", "REFUTED", "UNCLEAR"):
                verdict = "UNCLEAR"
            if len(reason) == 0 or len(reason) > 48:
                reason = "UNSPECIFIED"
            return json.dumps(
                {"verdict": verdict, "reason_code": reason}, sort_keys=True
            )

        def validator_fn(leader_result) -> bool:
            # Equivalence principle for this court: validators rerun the
            # whole evaluation independently and agree if and only if
            # their own verdict matches the leader's verdict. The
            # reason_code wording may legitimately differ between
            # independent LLM runs, so it is not part of the comparison.
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader_verdict = json.loads(leader_result.calldata)["verdict"]
                my_verdict = json.loads(evaluate())["verdict"]
            except Exception:
                return False
            return leader_verdict == my_verdict

        outcome = gl.vm.run_nondet(evaluate, validator_fn)
        result = json.loads(outcome)

        claim.status = "RESOLVED"
        claim.verdict = str(result["verdict"])
        claim.reason_code = str(result["reason_code"])
        self.claims[claim_id] = claim
        self.resolved_count = gl.u256(int(self.resolved_count) + 1)
        return claim.verdict

    @gl.public.view
    def get_claim(self, claim_id: str) -> dict:
        if claim_id not in self.claims:
            raise gl.vm.UserError("unknown claim id")
        c = self.claims[claim_id]
        return {
            "claim_id": c.claim_id,
            "claimant": c.claimant,
            "claim_text": c.claim_text,
            "evidence_url": c.evidence_url,
            "criteria": c.criteria,
            "status": c.status,
            "verdict": c.verdict,
            "reason_code": c.reason_code,
        }

    @gl.public.view
    def list_claim_ids(self) -> list:
        return [key for key in self.claims]

    @gl.public.view
    def get_stats(self) -> dict:
        total = int(self.claim_count)
        resolved = int(self.resolved_count)
        return {
            "claim_count": total,
            "resolved_count": resolved,
            "open_count": total - resolved,
        }
