"""Direct-mode tests for ClaimCourt (contracts/claim_court.py).

Web and LLM calls are mocked through the direct VM fixtures, so the suite
runs fully offline:  .venv/bin/python -m pytest tests/ -v
"""

import json

CONTRACT = "contracts/claim_court.py"
EVIDENCE_URL = "https://example.org/deliverables/report-42"
PAGE_OK = (
    "Final report 42. All acceptance tests pass. "
    "Delivered modules: parser, api, docs. Signed off by QA."
)
PAGE_MISSING = "Project page. Status: work in progress, nothing delivered yet."


def _file(contract, vm, sender, claim_id="case-1", url=EVIDENCE_URL):
    vm.sender = sender
    return contract.file_claim(
        claim_id,
        "The deliverable at the evidence page meets the acceptance criteria",
        url,
        "The page must state that all acceptance tests pass and list the "
        "delivered modules.",
    )


def _mock_judge(vm, page_body, verdict, reason_code):
    vm.mock_web(r".*example\.org/deliverables/.*", {"status": 200, "body": page_body})
    # response_format="json": the direct runner auto-parses the mock
    # string once and the SDK parses it again, so the payload must be
    # JSON-encoded twice (same convention as the official boilerplate's
    # mock_json_llm helper).
    vm.mock_llm(
        r".*ClaimCourt adjudication review.*",
        json.dumps(json.dumps({"verdict": verdict, "reason_code": reason_code})),
    )


def test_file_claim_stores_fields(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    returned = _file(contract, direct_vm, direct_alice)
    assert returned == "case-1"

    claim = contract.get_claim("case-1")
    assert claim["status"] == "OPEN"
    assert claim["verdict"] == ""
    assert claim["evidence_url"] == EVIDENCE_URL
    assert contract.list_claim_ids() == ["case-1"]
    stats = contract.get_stats()
    assert stats == {"claim_count": 1, "resolved_count": 0, "open_count": 1}


def test_duplicate_claim_rejected(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    _file(contract, direct_vm, direct_alice)
    with direct_vm.expect_revert("claim id already exists"):
        _file(contract, direct_vm, direct_alice)


def test_invalid_url_rejected(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("must be an http(s) URL"):
        contract.file_claim("case-x", "some claim", "ftp://nope", "criteria")


def test_adjudicate_supported(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    _file(contract, direct_vm, direct_alice)
    _mock_judge(direct_vm, PAGE_OK, "SUPPORTED", "CRITERIA_MET")

    outcome = contract.adjudicate("case-1")
    assert outcome == "SUPPORTED"

    claim = contract.get_claim("case-1")
    assert claim["status"] == "RESOLVED"
    assert claim["verdict"] == "SUPPORTED"
    assert claim["reason_code"] == "CRITERIA_MET"
    assert contract.get_stats()["resolved_count"] == 1


def test_adjudicate_refuted(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    _file(contract, direct_vm, direct_alice)
    _mock_judge(direct_vm, PAGE_MISSING, "REFUTED", "DELIVERABLE_MISSING")

    outcome = contract.adjudicate("case-1")
    assert outcome == "REFUTED"
    assert contract.get_claim("case-1")["reason_code"] == "DELIVERABLE_MISSING"


def test_adjudicate_unclear(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    _file(contract, direct_vm, direct_alice)
    _mock_judge(direct_vm, "Landing page with no project details.", "UNCLEAR",
                "EVIDENCE_INSUFFICIENT")

    outcome = contract.adjudicate("case-1")
    assert outcome == "UNCLEAR"


def test_double_adjudication_rejected(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    _file(contract, direct_vm, direct_alice)
    _mock_judge(direct_vm, PAGE_OK, "SUPPORTED", "CRITERIA_MET")
    contract.adjudicate("case-1")

    with direct_vm.expect_revert("claim already adjudicated"):
        contract.adjudicate("case-1")


def test_unknown_claim_rejected(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy(CONTRACT)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("unknown claim"):
        contract.adjudicate("nope")
