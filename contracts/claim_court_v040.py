# { "Depends": "py-genlayer:kzybg95x1gn21dw72m7hyg0maaap04n4nx55j9yt6fkdqxtz6bz0" }

import json
from dataclasses import dataclass

import genlayer as gl
from genlayer.types import *
from genlayer.storage import TreeMap


@gl.storage.allow
@dataclass
class Claim:
    claim_id: str
    claimant: str
    claim_text: str
    evidence_url: str
    criteria: str
    status: str
    verdict: str
    reason_code: str


class ClaimCourt(gl.contract.Contract):
    """Evidence-based claim adjudication court."""

    claims: TreeMap[str, Claim]
    claim_count: u256
    resolved_count: u256

    def __init__(self) -> None:
        self.claim_count = 0
        self.resolved_count = 0

    @gl.public.write
    def file_claim(self, claim_id: str, claim_text: str, evidence_url: str, criteria: str) -> str:
        if len(claim_id) == 0 or len(claim_id) > 64:
            raise gl.vm.UserError("claim_id must be 1..64 characters")
        if claim_id in self.claims:
            raise gl.vm.UserError("claim id already exists")
        if len(claim_text) == 0 or len(claim_text) > 500:
            raise gl.vm.UserError("claim_text must be 1..500 characters")
        if not (evidence_url.startswith("https://") or evidence_url.startswith("http://")):
            raise gl.vm.UserError("evidence_url must be an http(s) URL")
        if len(evidence_url) > 300:
            raise gl.vm.UserError("evidence_url too long")
        if len(criteria) == 0 or len(criteria) > 500:
            raise gl.vm.UserError("criteria must be 1..500 characters")
        self.claims[claim_id] = Claim(claim_id=claim_id, claimant=gl.message.sender_address.as_hex, claim_text=claim_text, evidence_url=evidence_url, criteria=criteria, status="OPEN", verdict="", reason_code="")
        self.claim_count = int(self.claim_count) + 1
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
            task = "ClaimCourt adjudication review. Judge the claim ONLY from the evidence page content below, applying the acceptance criteria exactly as written. Do not use outside knowledge and do not guess facts that are not on the page. CLAIM: " + claim_text + " ACCEPTANCE CRITERIA: " + criteria + " EVIDENCE PAGE CONTENT: " + page[:4000] + " Reply with a JSON object and nothing else: {\"verdict\": \"SUPPORTED\" | \"REFUTED\" | \"UNCLEAR\", \"reason_code\": \"SHORT_UPPER_SNAKE_CODE\"} Use SUPPORTED when the evidence clearly satisfies the criteria, REFUTED when the evidence clearly contradicts the claim or shows the criteria are not met, and UNCLEAR when the page does not contain enough information to decide."
            raw = gl.nondet.exec_prompt(task)
            if isinstance(raw, str):
                raw = raw.replace("```json", "").replace("```", "")
                raw = json.loads(raw)
            verdict = str(raw.get("verdict", "UNCLEAR")).strip().upper()
            if verdict not in ("SUPPORTED", "REFUTED", "UNCLEAR"):
                verdict = "UNCLEAR"
            return verdict
        verdict = gl.eq_principle.strict_eq(evaluate)
        if verdict == "SUPPORTED":
            reason_code = "EVIDENCE_SUPPORTS_CLAIM"
        elif verdict == "REFUTED":
            reason_code = "EVIDENCE_CONTRADICTS_CLAIM"
        else:
            reason_code = "INSUFFICIENT_EVIDENCE"
        claim.status = "RESOLVED"
        claim.verdict = verdict
        claim.reason_code = reason_code
        self.claims[claim_id] = claim
        self.resolved_count = int(self.resolved_count) + 1
        return claim.verdict

    @gl.public.view
    def get_claim(self, claim_id: str) -> dict:
        if claim_id not in self.claims:
            raise gl.vm.UserError("unknown claim id")
        c = self.claims[claim_id]
        return {"claim_id": c.claim_id, "claimant": c.claimant, "claim_text": c.claim_text, "evidence_url": c.evidence_url, "criteria": c.criteria, "status": c.status, "verdict": c.verdict, "reason_code": c.reason_code}

    @gl.public.view
    def list_claim_ids(self) -> list:
        return [key for key, value in self.claims.items()]

    @gl.public.view
    def get_stats(self) -> dict:
        total = int(self.claim_count)
        resolved = int(self.resolved_count)
        return {"claim_count": total, "resolved_count": resolved, "open_count": total - resolved}
