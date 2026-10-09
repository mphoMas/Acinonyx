"""Trusted coding adapter; validate evidence without rewriting signed schema v2."""
from pydantic import ValidationError

from mas.platform.contracts import CodingTaskAdmission, ContractError, TaskIdentity, VerificationEvidence
from mas.swarm.contracts import SwarmError, digest, exact_keys


def validate_coding_admission(document, request_key, actor):
    """Validate a freshly constructed host submission; never accept agent authority.

    The authenticated Store owns actor and request_key. Return its dictionary
    unchanged so historical signatures and persisted schema remain compatible.
    """
    try:
        parsed = CodingTaskAdmission(
            tenant_id=document["tenant"], task_id=document["id"], subject_id=document["submitted_by"],
            request_key=request_key, workflow="coding.solve.v1", request_hash=document["request_hash"],
            suite_hash=digest(document["request"]["cases"]), limits=document["request"]["limits"], created=document["created"],
        )
        if document["state"] != "queued" or type(document["version"]) is not int or document["version"] != 0:
            raise ContractError("Task admission requires a fresh queued submission")
        parsed.bind(actor["tenant"], actor["subject"], request_key, digest(document["request"]), digest(document["request"]["cases"]))
        return document
    except (ValidationError, ContractError, KeyError, TypeError) as exc:
        raise SwarmError("Coding task admission violates shared contract") from exc


def validate_coding_evidence(document, evidence, image):
    """Called by the host verifier, not exposed as an agent evidence tool.

    Preserve the existing evidence dictionary exactly. Shared contracts are an
    additional check, not a replacement for Store approval/provenance checks.
    """
    try:
        exact_keys(evidence, {"run_id", "candidate_hash", "suite_hash", "image", "provider", "results", "finished"})
        if evidence["run_id"] != document["id"] or evidence["provider"] != document["provider"]:
            raise ContractError("Evidence run or provider mismatch")
        identity = TaskIdentity(tenant_id=document["tenant"], task_id=document["id"], attempt_id=document["lease"], workflow="coding.solve.v1")
        results = []
        for result in evidence["results"]:
            exact_keys(result, {"id", "passed", "status"})
            results.append({"case_id": result["id"], "passed": result["passed"], "status": result["status"]})
        parsed = VerificationEvidence(
            identity=identity, candidate_hash=evidence["candidate_hash"], suite_hash=evidence["suite_hash"],
            executor_image=evidence["image"], verifier="coding-json-equality.v1", results=tuple(results), finished=evidence["finished"],
        )
        if document["candidate_hash"] != digest(document["source"]) or document["image"] != image:
            raise ContractError("Candidate or executor differs from claimed run")
        parsed.bind(identity, document["candidate_hash"], digest(document["request"]["cases"]), image,
                    tuple(case["id"] for case in document["request"]["cases"]))
        return evidence
    except (ValidationError, ContractError, KeyError, TypeError) as exc:
        raise SwarmError("Coding verification evidence violates shared contract") from exc
