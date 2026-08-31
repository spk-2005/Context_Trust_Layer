import unittest
from datetime import datetime, timezone, timedelta
from app.trust_engine.calculator import TrustScoreCalculator


class TestTrustScoreCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = TrustScoreCalculator()

    def test_freshness_decay(self):
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)
        two_years_ago = now - timedelta(days=730)

        freshness_now = self.calculator.calculate_freshness(now)
        freshness_1yr = self.calculator.calculate_freshness(one_year_ago)
        freshness_2yr = self.calculator.calculate_freshness(two_years_ago)

        self.assertAlmostEqual(freshness_now, 1.0, places=2)
        # Half life is 365 days -> ~0.50
        self.assertAlmostEqual(freshness_1yr, 0.50, places=2)
        # 2 half lives -> ~0.25
        self.assertAlmostEqual(freshness_2yr, 0.25, places=2)

    def test_high_authority_fresh_document_score(self):
        now = datetime.now(timezone.utc)
        breakdown = self.calculator.calculate(
            source_authority_level=90,
            doc_created_at=now,
            has_evidence=True,
            is_current_version=True,
            has_conflicts=False,
        )

        self.assertGreaterEqual(float(breakdown.overall_score), 0.85)
        self.assertEqual(float(breakdown.source_score), 0.90)
        self.assertEqual(float(breakdown.consistency_score), 1.00)

    def test_conflict_penalty_on_trust_score(self):
        now = datetime.now(timezone.utc)
        score_normal = self.calculator.calculate(
            source_authority_level=80,
            doc_created_at=now,
            has_conflicts=False,
        )
        score_conflicted = self.calculator.calculate(
            source_authority_level=80,
            doc_created_at=now,
            has_conflicts=True,
            conflict_confidence=0.90,
        )

        self.assertGreater(
            float(score_normal.overall_score),
            float(score_conflicted.overall_score)
        )
        self.assertLess(float(score_conflicted.consistency_score), 0.50)


if __name__ == "__main__":
    unittest.main()
