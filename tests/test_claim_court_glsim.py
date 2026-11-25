"""GLSim integration tests for ClaimCourt (contracts/claim_court.py).

Runs against a local GLSim node (no Docker, no real network/LLM):
    GENVM_VERSION=v0.3.0-rc7 .venv/bin/glsim --port 4000 --no-browser &
    GENVM_VERSION=v0.3.0-rc7 .venv/bin/gltest tests/test_claim_court_glsim.py -v

Web and LLM responses are pinned through GLSim's persistent mock RPC
(sim_installMocks, strict mode) so adjudication is fully deterministic.
Client API note: contract.m(args=[...]) returns a ContractFunction;
views execute via .call(), writes via .transact(...).
"""

import json

import pytest
import requests
from gltest import get_contract_factory

RPC_URL = "http://127.0.0.1:4000/api"
EVIDENCE_URL = "https://example.org/deliverables/report-42"
PAGE_OK = (
    "Final report 42. All acceptance tests pass. "
    "Delivered modules: parser, api, docs. Signed off by QA."
)
CLAIM_TEXT = "The deliverable at the evidence page meets the acceptance criteria"
CRITERIA = (
    "The page must state that all acceptance tests pass and list the "
    "delivered modules."
)


def _install_mocks(page_body: str, verdict: str, reason_code: str) -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sim_installMocks",
        "params": {
            "web_mocks": {
                r".*example\.org/deliverables/.*": {
                    "status": 200,
                    "body": page_body,
                }
            },
            "llm_mocks": {
                # double-encoded: runner auto-parses once, SDK parses again
                r".*ClaimCourt adjudication review.*": json.dumps(
                    json.dumps({"verdict": verdict, "reason_code": reason_code})
                )
            },
            "strict": True,
        },
    }
    resp = requests.post(RPC_URL, json=payload, timeout=30)
    result = resp.json()
    assert "result" in result, f"sim_installMocks failed: {result}"


def _deploy():
    factory = get_contract_factory("ClaimCourt")
    return factory.deploy()


def _write(contract, method, args):
    return getattr(contract, method)(args=args).transact(
        wait_interval=2000, wait_retries=30
    )


def _read(contract, method, args):
    return getattr(contract, method)(args=args).call()


@pytest.mark.integration
def test_glsim_file_and_adjudicate_supported():
    contract = _deploy()

    _write(contract, "file_claim", ["case-1", CLAIM_TEXT, EVIDENCE_URL, CRITERIA])

    claim = _read(contract, "get_claim", ["case-1"])
    assert claim["status"] == "OPEN"
    assert claim["verdict"] == ""
    assert _read(contract, "get_stats", []) == {
        "claim_count": 1,
        "resolved_count": 0,
        "open_count": 1,
    }

    _install_mocks(PAGE_OK, "SUPPORTED", "CRITERIA_MET")
    _write(contract, "adjudicate", ["case-1"])

    claim = _read(contract, "get_claim", ["case-1"])
    assert claim["status"] == "RESOLVED"
    assert claim["verdict"] == "SUPPORTED"
    assert claim["reason_code"] == "CRITERIA_MET"
    assert _read(contract, "get_stats", [])["resolved_count"] == 1
    assert _read(contract, "list_claim_ids", []) == ["case-1"]


@pytest.mark.integration
def test_glsim_adjudicate_refuted():
    contract = _deploy()
    _write(contract, "file_claim", ["case-9", CLAIM_TEXT, EVIDENCE_URL, CRITERIA])

    _install_mocks(
        "Project page. Status: work in progress, nothing delivered yet.",
        "REFUTED",
        "DELIVERABLE_MISSING",
    )
    _write(contract, "adjudicate", ["case-9"])

    claim = _read(contract, "get_claim", ["case-9"])
    assert claim["verdict"] == "REFUTED"
    assert claim["reason_code"] == "DELIVERABLE_MISSING"
