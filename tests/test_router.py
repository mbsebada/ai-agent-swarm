"""Behavior tests for examples/router.py (standard library unittest).

Run from the repo root:  python3 -m unittest discover -s tests -v

What these tests are for:
- The README and HOW_IT_WORKS.md make specific claims about how the demo
  behaves: which agent gets which message, that failures and budget skips
  are reported separately, that nothing is charged for a failed call, and
  that the breaker stops paid calls at zero credits. Each claim has a test
  here, so a later edit cannot quietly make the documentation wrong.
- One test compares the whole demo run against expected_output.txt. It is
  the broadest check: any change to routing, costs, wording or the seed
  shows up there first.

How the tests control randomness:
- The demo's outages are random. Tests that need a particular outcome do
  not depend on the random seed; they either set failure_rate to 0.0
  (nothing fails) or 1.0 (everything fails), or they replace call_model()
  with a stand-in that fails exactly when the test says so.

How to read a failure:
- unittest prints the test's name and its one-line description (the first
  line of each docstring below), then the line that did not match. The
  description says which documented behavior has broken.

Each test, and the claim it protects:
- test_demo_output_matches_expected_file: the walkthrough's ten lines are
  exactly what the demo prints.
- test_known_categories: each keyword family reaches its own category.
- test_security_wins_over_code: security is checked before code.
- test_unknown_falls_back_to_default: unmatched messages still get answered.
- test_every_category_has_an_agent: no category is ever left without owner.
- test_success_reports_model_and_cost: reports name the answering model and
  only its cost is charged.
- test_skipped_and_failed_are_reported_separately: a budget skip and an
  outage are never described as the same thing.
- test_all_models_failing_is_not_success: an outage is never reported as an
  answer, and is never charged.
- test_mixed_failure_and_skip_is_not_called_all_failed: "all failed" is
  never claimed when a model was only skipped.
- test_breaker_opens_at_zero_and_calls_no_paid_model: an empty budget stops
  every paid call, and the alert is not claimed as sent.
- test_refill_restores_budget: a new day restores full budgets.
- test_negative_charge_rejected: the cap cannot be bypassed by a negative
  charge.

Adding a test:
- Put it in the class for the part of the demo it checks.
- Give it a one-line description first in its docstring; that line is what
  appears in the test report.
- Control randomness with failure_rate 0.0 or 1.0, or a scripted stand-in
  for call_model(); never rely on the seed except in the full-output test.
- Check what the report SAYS as well as what the ledger HOLDS: the demo's
  whole point is that its reports are honest.

What the tests do not cover:
- Real providers, real money, or real alerts: the demo has none.
- Timing and concurrency: the demo handles one message at a time.

Layout:
- DemoOutputTest: the full seeded run, line for line.
- ClassifyTest: sorting messages into categories.
- RoutingTest: the fallback chain and what the report says about it.
- BreakerTest: the daily spend cap.
"""

# === Setup ===
# Everything below this banner runs once, when the test file is loaded;
# the test classes further down run afterwards, one test at a time.
# Standard library only, matching the demo: nothing to install.
# contextlib and io let a test capture what the demo prints.
import contextlib  # capture printed output
import io  # in-memory text files

# sys and Path are used to make the examples folder importable.
import sys  # the import path
import unittest  # the test framework
from pathlib import Path  # file paths

# mock replaces call_model() with a stand-in for scenario tests.
from unittest import mock  # stand-ins for real functions

# examples/ is a plain folder, not a package, so add it to the import path.
# The path is worked out from this file's location, so the tests run the
# same way from any current directory.
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
sys.path.insert(0, str(EXAMPLES_DIR))  # search examples/ first

# Import the demo itself; importing also runs its startup check, so a
# category without an owner would fail here, before any test starts.
# The noqa note on the import line tells style checkers the late import
# is deliberate: it has to come after the path change above.
import router  # noqa: E402


# === Tests ===
# Four groups, one per part of the demo. Each test builds its own fresh
# ledger, so no test can be affected by another's spending.
class DemoOutputTest(unittest.TestCase):
    """The whole demo, compared with the saved copy of its output.

    This is the widest net: it notices any change to routing, costs, the
    seed or the wording of a report line, all at once. The narrower tests
    below then say which specific behavior moved.
    """

    def test_demo_output_matches_expected_file(self):
        """The seeded demo prints exactly what expected_output.txt records.

        Why it matters: HOW_IT_WORKS.md walks through these exact lines. If
        the output drifts, the walkthrough is wrong, and this test says so.
        If a change is meant to alter the output, re-run the demo and save
        the new output over expected_output.txt.

        If this fails: the demo's output changed; decide whether that was meant, and if so
        save the new output over expected_output.txt.
        """
        # A StringIO is an in-memory text file that collects printed lines.
        captured = io.StringIO()  # empty to start
        # While inside this block, print() writes to `captured`, not the screen.
        with contextlib.redirect_stdout(captured):  # capture prints
            # Run the full ten-message demo with its fixed seed.
            router.main()  # ten report lines
        # The saved, known-good output.
        expected = (EXAMPLES_DIR / "expected_output.txt").read_text()  # known-good copy
        # Every character must match, including spacing and line endings.
        self.assertEqual(captured.getvalue(), expected)  # exact match


class ClassifyTest(unittest.TestCase):
    """Sorting messages into categories, the first step of every message.

    A wrong category sends a message to the wrong agent and the wrong
    models, so these checks guard the start of the whole pipeline.
    """

    def test_known_categories(self):
        """Each keyword family lands in its own category.

        One representative message per category, so a renamed or missing
        keyword list is caught immediately.

        If this fails: a keyword list was renamed, emptied or moved; check
        CATEGORY_KEYWORDS in router.py.
        """
        # A threat-shaped message goes to security.
        self.assertEqual(router.classify("suspicious ssh login"), "security")
        # A programming message goes to code.
        self.assertEqual(router.classify("fix this python traceback"), "code")
        # A server chore is ops (and stays with the Hub).
        self.assertEqual(router.classify("restart the server"), "ops")
        # Small talk is trivial.
        self.assertEqual(router.classify("hi there"), "trivial")

    def test_security_wins_over_code(self):
        """Category order matters: a security event mentioning code is security.

        The README says the specific categories are checked first. A message
        with both a code word ("python") and a security word ("leak") must go
        to the security agent, because missing a security event costs more.

        If this fails: the order of CATEGORY_KEYWORDS changed; security must
        stay first.
        """
        # Both families match; security must win.
        self.assertEqual(router.classify("python script leak"), "security")

    def test_unknown_falls_back_to_default(self):
        """A message with no keywords goes to the default category.

        Ordinary requests must still be answered (by the Hub), never dropped.

        If this fails: DEFAULT_CATEGORY was changed or classify() no longer
        falls back to it.
        """
        # No keyword from any list appears in this message.
        self.assertEqual(router.classify("summarize this article"), router.DEFAULT_CATEGORY)

    def test_every_category_has_an_agent(self):
        """classify() can never return a category nobody owns.

        The demo also checks this at startup; this test keeps the guarantee
        visible in the test report.

        If this fails: a category was added to CATEGORY_KEYWORDS without an
        owner in CATEGORY_TO_AGENT.
        """
        # Every keyword category, plus the default one.
        for category_name in list(router.CATEGORY_KEYWORDS) + [router.DEFAULT_CATEGORY]:  # all six categories
            # Each must appear in the routing table.
            self.assertIn(category_name, router.CATEGORY_TO_AGENT)


class RoutingTest(unittest.TestCase):
    """The fallback chain, and what the report line says about it.

    These tests force specific outcomes (success, outage, budget skip) and
    then read the report, because an honest report is the demo's point.
    """

    def test_success_reports_model_and_cost(self):
        """A successful call names the model that answered and charges it.

        Scenario: nothing fails, so the Hub's first model answers. The report
        must name it, and exactly its cost must come off the budget.

        If this fails: the success report or the charging changed.
        """
        # A fresh ledger: every agent starts with 10 credits.
        ledger = router.CreditLedger(daily_budget=10)  # 10 credits each
        # failure_rate 0.0 means no call ever fails.
        report = router.handle("hi thanks", ledger, failure_rate=0.0)  # nothing fails
        # The report says which model replied.
        self.assertIn("answered by provider-a/small-fast", report)
        # That model costs 1, so 9 credits remain.
        self.assertEqual(ledger.balance("hub"), 9)

    def test_skipped_and_failed_are_reported_separately(self):
        """Over-budget models are 'skipped', models that error are 'failed'.

        Scenario: the code agent has 4 credits. The cost-5 specialist is
        unaffordable (skipped), the general model is forced to fail, and the
        cheapest model answers. All three facts must appear in the report;
        lumping them together would hide a silent downgrade.

        If this fails: handle() is merging skips and failures again,
        which hides downgrades.
        """
        # Only 4 credits: the cost-5 code specialist cannot be afforded.
        ledger = router.CreditLedger(daily_budget=4)  # 4 credits
        # The scripted outcomes, in call order: first call fails, second works.
        outcomes = iter([router.ModelUnavailable("down"), "ok"])  # fail, then succeed

        def fake_call(*_args):  # accepts any arguments
            """Fail the first call, succeed on the second.

            Stands in for call_model(), so the test decides exactly which
            model attempt fails instead of leaving it to chance.
            """
            # Take the next scripted outcome.
            outcome = next(outcomes)  # next scripted result
            # A scripted error is raised, just as a real outage would be.
            if isinstance(outcome, Exception):  # scripted failure?
                raise outcome  # simulate the outage
            # Otherwise behave like a successful model reply.
            return outcome  # simulate a reply

        # Swap in the scripted stand-in for the duration of this block only.
        with mock.patch.object(router, "call_model", side_effect=fake_call):  # swap in the script
            # A code message, so the code agent's chain is used.
            report = router.handle("python bug", ledger)  # code agent's chain
        # The specialist was never called: reported as a budget skip.
        self.assertIn("skipped (over budget): provider-c/code-specialized", report)
        # The general model was called and failed: reported as a failure.
        self.assertIn("failed: provider-c/general", report)
        # The cheapest model answered, and the report says so.
        self.assertIn("answered by provider-a/small-fast", report)

    def test_all_models_failing_is_not_success(self):
        """Every model down with budget left: reported as unanswered, not charged.

        Scenario: every Hub model fails. The demo must say NO MODEL ANSWERED
        (never a fake success), list each failure, and charge nothing.

        If this fails: an outage is being reported as an answer or charged.
        """
        # Plenty of budget, so nothing is skipped for cost.
        ledger = router.CreditLedger(daily_budget=10)  # 10 credits each
        # failure_rate 1.0 means every call fails.
        report = router.handle("hi thanks", ledger, failure_rate=1.0)  # everything fails
        # The outcome is stated plainly.
        self.assertIn("NO MODEL ANSWERED", report)
        # All three Hub models are listed as failed, in chain order.
        self.assertIn("failed: provider-a/small-fast, provider-b/small-fast, provider-c/mid-tier", report)
        # Failures are not charged, so the budget is untouched.
        self.assertEqual(ledger.balance("hub"), 10)

    def test_mixed_failure_and_skip_is_not_called_all_failed(self):
        """With 2 credits the cost-3 Hub model is skipped, not reported as failed.

        Scenario: the two cheap Hub models fail and the third is too
        expensive. Saying "all failed" would be false: one was never tried.

        If this fails: skipped models are being listed as failed.
        """
        # 2 credits: the cost-3 model is out of reach.
        ledger = router.CreditLedger(daily_budget=2)  # 2 credits
        # Every call that is attempted fails.
        report = router.handle("hi thanks", ledger, failure_rate=1.0)  # everything fails
        # Nobody answered.
        self.assertIn("NO MODEL ANSWERED", report)
        # The expensive model is correctly listed as skipped.
        self.assertIn("skipped (over budget): provider-c/mid-tier", report)
        # And it is NOT listed among the failures.
        self.assertNotIn("failed: provider-a/small-fast, provider-b/small-fast, provider-c", report)


class BreakerTest(unittest.TestCase):
    """The daily spend cap: what happens when an agent runs out of credits.

    The cap exists to stop a runaway loop from running up a bill, so these
    tests check that it cannot be skipped, bypassed or faked.
    """

    def test_breaker_opens_at_zero_and_calls_no_paid_model(self):
        """Zero budget: no paid model is called and the alert is labeled simulated.

        Scenario: the agent has no credits. The breaker must stop before any
        paid call, and the report must not claim an alert was really sent.

        If this fails: the breaker check moved below the loop, or the
        report claims a real alert.
        """
        # An agent that starts the day with nothing.
        ledger = router.CreditLedger(daily_budget=0)  # no credits
        # Replace call_model() with a recorder that notes any call made.
        with mock.patch.object(router, "call_model") as paid_call:  # record any call
            # A code message; the code agent's cheapest model costs 1.
            report = router.handle("python bug", ledger)  # code agent's chain
        # Not a single paid model was called.
        paid_call.assert_not_called()  # zero paid calls
        # The report says the breaker opened.
        self.assertIn("BREAKER OPEN", report)
        # The alert is described as simulated...
        self.assertIn("alert would fire (simulated)", report)
        # ...and never claimed as actually sent.
        self.assertNotIn("ALERT sent", report)

    def test_refill_restores_budget(self):
        """A new day gives every agent its full budget back.

        Scenario: an agent spends everything, then the day rolls over.

        If this fails: refill_all() no longer resets balances.
        """
        # Five credits per agent.
        ledger = router.CreditLedger(daily_budget=5)  # 5 credits each
        # Spend all of the code agent's credits.
        ledger.charge("code", 5)  # spend it all
        # Start a new day.
        ledger.refill_all()  # new day
        # The code agent is back to its full five.
        self.assertEqual(ledger.balance("code"), 5)

    def test_negative_charge_rejected(self):
        """The ledger refuses a negative cost (it would add credits).

        A negative charge would quietly raise an agent's budget and defeat
        the cap, so it must fail loudly instead.

        If this fails: the guard in CreditLedger.charge() was removed.
        """
        # assertRaises passes only if the block raises ValueError.
        with self.assertRaises(ValueError):  # must raise
            # Try to "charge" minus one credit.
            router.CreditLedger().charge("hub", -1)  # minus one credit


# Allow running this file directly as well as through unittest discovery.
# Either way the same twelve tests run and the same report is printed.
# Running it directly is handy when working on one part of the demo.
if __name__ == "__main__":
    unittest.main()  # run every test here
