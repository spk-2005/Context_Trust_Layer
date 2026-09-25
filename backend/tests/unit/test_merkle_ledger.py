import uuid
import pytest

from app.schemas.merkle import MerkleProofStep
from app.services.merkle_service import (
    build_merkle_tree,
    generate_compliance_certificate,
    generate_merkle_proof,
    hash_leaf,
    verify_merkle_proof,
)


def test_merkle_tree_empty_and_single():
    empty_root, levels = build_merkle_tree([])
    assert len(empty_root) == 64

    single_root, levels = build_merkle_tree(["tok_1"])
    assert len(single_root) == 64
    assert single_root == hash_leaf("tok_1")


def test_merkle_tree_even_and_odd_leaves():
    leaves_4 = ["tok_1", "tok_2", "tok_3", "tok_4"]
    root_4, levels_4 = build_merkle_tree(leaves_4)
    assert len(root_4) == 64
    assert len(levels_4) == 3  # leaves, pairs, root

    leaves_3 = ["tok_1", "tok_2", "tok_3"]
    root_3, levels_3 = build_merkle_tree(leaves_3)
    assert len(root_3) == 64
    assert len(levels_3) == 3


def test_merkle_proof_generation_and_positive_verification():
    tokens = [f"audit_tok_{i}" for i in range(8)]
    target_token = "audit_tok_3"

    root_hash, _ = build_merkle_tree(tokens)
    proof_resp = generate_merkle_proof(target_token, tokens)

    assert proof_resp is not None
    assert proof_resp.audit_token == target_token
    assert proof_resp.root_hash == root_hash
    assert len(proof_resp.proof_path) == 3  # log2(8) = 3 steps

    # Verify proof independently
    is_valid, computed_root = verify_merkle_proof(
        target_token, root_hash, proof_resp.proof_path
    )
    assert is_valid is True
    assert computed_root == root_hash


def test_merkle_proof_negative_tamper():
    tokens = ["tok_a", "tok_b", "tok_c", "tok_d"]
    root_hash, _ = build_merkle_tree(tokens)
    proof_resp = generate_merkle_proof("tok_a", tokens)

    # Tamper with token
    is_valid, _ = verify_merkle_proof("tok_tampered", root_hash, proof_resp.proof_path)
    assert is_valid is False

    # Tamper with proof step
    tampered_path = [
        MerkleProofStep(hash="0" * 64, direction=proof_resp.proof_path[0].direction)
    ] + proof_resp.proof_path[1:]
    is_valid_step, _ = verify_merkle_proof("tok_a", root_hash, tampered_path)
    assert is_valid_step is False


@pytest.mark.asyncio
async def test_generate_compliance_certificate():
    org_id = uuid.uuid4()
    cert = await generate_compliance_certificate(
        "audit_tok_11223344556677889900", org_id, session=None
    )
    assert cert.certificate_id.startswith("CERT-EU12-")
    assert cert.root_hash is not None
    assert cert.tamper_evident is True
    assert len(cert.compliance_seal) == 64
