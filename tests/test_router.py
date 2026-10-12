"""Behaviour tests for examples/router.py (standard library unittest).

Run from the repo root:  python3 -m unittest discover -s tests -v
"""

# === Setup ===
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest import mock

# examples/ is not a package, so put it on the import path.
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
sys.path.insert(0, str(EXAMPLES_DIR))

import router  # noqa: E402  (import after the path tweak above)


# === Tests ===
class DemoOutputTest(unittest.TestCase):
    def test_demo_output_matches_expected_file(self):
        """The seeded demo prints exactly what expected_output.txt records."""
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            router.main()
        expected = (EXAMPLES_DIR / "expected_output.txt").read_text()
        self.assertEqual(captured.getvalue(), expected)


class ClassifyTest(unittest.TestCase):
    def test_known_categories(self):
        """Each keyword family lands in its own category."""
        self.assertEqual(router.classify("suspicious ssh login"), "security")
        self.assertEqual(router.classify("fix this python traceback"), "code")
        self.assertEqual(router.classify("restart the server"), "ops")
        self.assertEqual(router.classify("hi there"), "trivial")

    def test_security_wins_over_code(self):
        """Category order matters: a security event mentioning code is security."""
        self.assertEqual(router.classify("python script leak"), "security")

    def test_unknown_falls_back_to_default(self):
        """A message with no keywords goes to the default category."""
        self.assertEqual(router.classify("summarize this article"), router.DEFAULT_CATEGORY)

    def test_every_category_has_an_agent(self):
        """classify() can never return a category nobody owns."""
        for category_name in list(router.CATEGORY_KEYWORDS) + [router.DEFAULT_CATEGORY]:
            self.assertIn(category_name, router.CATEGORY_TO_AGENT)


class RoutingTest(unittest.TestCase):
    def test_success_reports_model_and_cost(self):
        """A successful call names the model that answered and charges it."""
        ledger = router.CreditLedger(daily_budget=10)
        report = router.handle("hi thanks", ledger, failure_rate=0.0)
        self.assertIn("answered by provider-a/small-fast", report)
        self.assertEqual(ledger.balance("hub"), 9)

    def test_skipped_and_failed_are_reported_separately(self):
        """Over-budget models are 'skipped', models that error are 'failed'."""
        ledger = router.CreditLedger(daily_budget=4)  # cannot afford the cost-5 code model
        outcomes = iter([router.ModelUnavailable("down"), "ok"])

        def fake_call(*_args):
            """Fail the first call, succeed on the second."""
            outcome = next(outcomes)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        with mock.patch.object(router, "call_model", side_effect=fake_call):
            report = router.handle("python bug", ledger)
        self.assertIn("skipped (over budget): provider-c/code-specialized", report)
        self.assertIn("failed: provider-c/general", report)
        self.assertIn("answered by provider-a/small-fast", report)

    def test_all_models_failing_is_not_success(self):
        """Every model down with budget left: reported as unanswered, not charged."""
        ledger = router.CreditLedger(daily_budget=10)
        report = router.handle("hi thanks", ledger, failure_rate=1.0)
        self.assertIn("NO MODEL ANSWERED", report)
        self.assertIn("failed: provider-a/small-fast, provider-b/small-fast, provider-c/mid-tier", report)
        self.assertEqual(ledger.balance("hub"), 10)  # failures are not charged

    def test_mixed_failure_and_skip_is_not_called_all_failed(self):
        """With 2 credits the cost-3 Hub model is skipped, not reported as failed."""
        ledger = router.CreditLedger(daily_budget=2)
        report = router.handle("hi thanks", ledger, failure_rate=1.0)
        self.assertIn("NO MODEL ANSWERED", report)
        self.assertIn("skipped (over budget): provider-c/mid-tier", report)
        self.assertNotIn("failed: provider-a/small-fast, provider-b/small-fast, provider-c", report)


class BreakerTest(unittest.TestCase):
    def test_breaker_opens_at_zero_and_calls_no_paid_model(self):
        """Zero budget: no paid model is called and the alert is labelled simulated."""
        ledger = router.CreditLedger(daily_budget=0)
        with mock.patch.object(router, "call_model") as paid_call:
            report = router.handle("python bug", ledger)
        paid_call.assert_not_called()
        self.assertIn("BREAKER OPEN", report)
        self.assertIn("alert would fire (simulated)", report)
        self.assertNotIn("ALERT sent", report)

    def test_refill_restores_budget(self):
        """A new day gives every agent its full budget back."""
        ledger = router.CreditLedger(daily_budget=5)
        ledger.charge("code", 5)
        ledger.refill_all()
        self.assertEqual(ledger.balance("code"), 5)

    def test_negative_charge_rejected(self):
        """The ledger refuses a negative cost (it would add credits)."""
        with self.assertRaises(ValueError):
            router.CreditLedger().charge("hub", -1)


if __name__ == "__main__":
    unittest.main()
