import unittest
import asyncio
from app.llm.mock_provider import MockLLMProvider


class TestMockLLMProvider(unittest.TestCase):
    def setUp(self):
        self.provider = MockLLMProvider(embedding_dim=1536)

    def test_extract_claims_from_policy(self):
        async def run_test():
            content = (
                "All full-time employees receive 25 days of annual leave per year. "
                "Employees are granted $500 home office setup allowance."
            )
            result = await self.provider.extract_claims(
                document_title="Employee Benefits 2026",
                section_title="Leave & Allowances",
                section_content=content,
            )
            self.assertEqual(len(result.claims), 2)
            self.assertEqual(result.claims[0].predicate, "receive")
            self.assertIn("25 days", result.claims[0].object)
            self.assertEqual(result.claims[1].predicate, "are granted")
            self.assertIn("$500", result.claims[1].object)

        asyncio.run(run_test())

    def test_get_embedding_deterministic_and_unit_norm(self):
        async def run_test():
            text = "Full-time annual leave policy"
            vec1 = await self.provider.get_embedding(text)
            vec2 = await self.provider.get_embedding(text)

            self.assertEqual(len(vec1), 1536)
            self.assertEqual(vec1, vec2)

            # Check L2 norm is ~1.0
            norm = sum(v * v for v in vec1) ** 0.5
            self.assertAlmostEqual(norm, 1.0, places=4)

        asyncio.run(run_test())

    def test_evaluate_contradiction_numerical_discrepancy(self):
        async def run_test():
            claim_a = "All full-time employees receive 20 days of annual leave."
            claim_b = "All full-time employees receive 25 days of annual leave."

            eval_res = await self.provider.evaluate_contradiction(claim_a, claim_b)
            self.assertTrue(eval_res.is_contradiction)
            self.assertEqual(eval_res.conflict_type, "numerical_discrepancy")
            self.assertEqual(eval_res.severity, "high")

        asyncio.run(run_test())

    def test_evaluate_contradiction_direct_opposition(self):
        async def run_test():
            claim_a = "Remote work is allowed for engineering staff."
            claim_b = "Remote work is prohibited for engineering staff."

            eval_res = await self.provider.evaluate_contradiction(claim_a, claim_b)
            self.assertTrue(eval_res.is_contradiction)
            self.assertEqual(eval_res.conflict_type, "direct_contradiction")

        asyncio.run(run_test())

    def test_evaluate_contradiction_page_header_compatible(self):
        async def run_test():
            claim_a = "SS FINANCE ARCHITECT 01 Customer Refund & Disputes Policy Document ID: SSFA-01 | Version: 2026.2 | Authority: 85 Chapter 1: Refund Page 1 Section purpose: Refunds, disputes, settlement authority."
            claim_b = "Chapter 1: Refund Page 2 Section purpose: Refunds, disputes, settlement authority."
            claim_c = "Refund example: transaction RF-01-001; standard automated limit $2,500; Enterprise exception limit $10,000."

            eval_res_headers = await self.provider.evaluate_contradiction(claim_a, claim_b)
            self.assertFalse(eval_res_headers.is_contradiction)
            self.assertEqual(eval_res_headers.conflict_type, "compatible")

            eval_res_meta_vs_rule = await self.provider.evaluate_contradiction(claim_a, claim_c)
            self.assertFalse(eval_res_meta_vs_rule.is_contradiction)
            self.assertEqual(eval_res_meta_vs_rule.conflict_type, "compatible")

        asyncio.run(run_test())

    def test_evaluate_contradiction_true_currency_discrepancy(self):
        async def run_test():
            claim_a = "Standard automated refund limit is $2,500."
            claim_b = "Standard automated refund limit is $1,000."

            eval_res = await self.provider.evaluate_contradiction(claim_a, claim_b)
            self.assertTrue(eval_res.is_contradiction)
            self.assertEqual(eval_res.conflict_type, "numerical_discrepancy")

        asyncio.run(run_test())

    def test_evaluate_contradiction_segregation_of_duties_compatible(self):
        async def run_test():
            claim_a = "Control rule 1.1.1: Every transaction must have a traceable transaction identifier, business purpose, responsible owner, approval timestamp and supporting evidence."
            claim_b = "Approval principle: A person must not approve their own transaction."

            eval_res = await self.provider.evaluate_contradiction(claim_a, claim_b)
            self.assertFalse(eval_res.is_contradiction)
            self.assertEqual(eval_res.conflict_type, "compatible")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
