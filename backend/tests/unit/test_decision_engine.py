import asyncio
import unittest

from app.decision_engine.evaluator import DecisionEvaluator
from app.schemas.decision import (
    DecisionActor,
    DecisionContextItem,
    DecisionEvaluateRequest,
)


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.evaluator = DecisionEvaluator()

    def test_outdated_policy_trap_review_outcome(self):
        """Simulates Section 23 of the Blueprint: 30-day handbook vs 60-day enterprise exception."""
        async def run_test():
            req = DecisionEvaluateRequest(
                decision="Determine whether customer is eligible for refund",
                actor=DecisionActor(id="agent-42", role="support"),
                context=[
                    DecisionContextItem(
                        claim="Refund window is 30 days",
                        source="handbook.pdf",
                        updated_at="2025-11-04",
                        authority_level=50,
                    ),
                    DecisionContextItem(
                        claim="Enterprise customers have a 60-day exception",
                        source="policy-service",
                        updated_at="2026-08-25",
                        authority_level=90,
                    ),
                ],
            )
            res = await self.evaluator.evaluate(req)

            self.assertEqual(res.decision, "REVIEW")
            self.assertEqual(res.validity, "INSUFFICIENT")
            self.assertEqual(res.risk, "HIGH")
            self.assertEqual(res.preferred_source, "policy-service")
            self.assertTrue(len(res.reasons) >= 2)
            self.assertIn("Conflicting policy evidence", res.reasons[0])
            self.assertTrue(res.audit_id.startswith("ctx_"))

        asyncio.run(run_test())

    def test_allow_outcome_with_consistent_evidence(self):
        """Tests that clean, non-conflicting authoritative evidence yields ALLOW and LOW risk."""
        async def run_test():
            req = DecisionEvaluateRequest(
                decision="Determine whether customer is eligible for refund",
                actor=DecisionActor(id="agent-42", role="support"),
                context=[
                    DecisionContextItem(
                        claim="Enterprise customers have a 60-day exception",
                        source="policy-service",
                        updated_at="2026-08-25",
                        authority_level=90,
                    ),
                ],
            )
            res = await self.evaluator.evaluate(req)

            self.assertEqual(res.decision, "ALLOW")
            self.assertEqual(res.validity, "VALID")
            self.assertEqual(res.risk, "LOW")
            self.assertEqual(res.preferred_source, "policy-service")

        asyncio.run(run_test())

    def test_block_unauthorized_actor_role(self):
        """Tests that unauthorized actors are blocked immediately."""
        async def run_test():
            req = DecisionEvaluateRequest(
                decision="Grant refund exception override",
                actor=DecisionActor(id="guest-bot", role="viewer"),
                context=[
                    DecisionContextItem(
                        claim="Refund window is 30 days",
                        source="handbook.pdf",
                        updated_at="2025-11-04",
                    ),
                ],
            )
            res = await self.evaluator.evaluate(req)

            self.assertEqual(res.decision, "BLOCK")
            self.assertEqual(res.risk, "HIGH")
            self.assertIn("not authorized", res.reasons[0])

        asyncio.run(run_test())

    def test_clarify_outcome_on_empty_context(self):
        """Tests that missing evidence triggers CLARIFY."""
        async def run_test():
            req = DecisionEvaluateRequest(
                decision="Determine refund eligibility",
                actor=DecisionActor(id="agent-42", role="support"),
                context=[],
            )
            res = await self.evaluator.evaluate(req)

            self.assertEqual(res.decision, "CLARIFY")
            self.assertEqual(res.validity, "INSUFFICIENT")
            self.assertEqual(res.risk, "MEDIUM")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
