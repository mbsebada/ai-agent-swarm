#!/usr/bin/env python3
"""
router.py: a small, runnable sketch of the three ideas behind the AI Agent Swarm.

1. Classify: sort an incoming message into a category.
2. Route: send it to the agent that owns that category, then walk the agent's
   fallback chain (an ordered list of models from different providers) until
   one answers.
3. Spend cap ("circuit breaker"): each agent has a daily credit budget. When
   it is exhausted, paid models are no longer called; the message gets a
   free-tier answer and an alert is raised for a human to investigate.

This is an illustration, not the production system (which is private because
it holds API keys and personal data). It makes no network calls: the models
are fake functions that fail at random so failover can be seen. Plain-English
walkthrough: HOW_IT_WORKS.md. Expected output: expected_output.txt.

Deliberate simplifications:
- Classification uses keywords. The real Hub uses a model to classify; the
  keywords are a deterministic, free stand-in.
- If every paid model in a chain fails while budget remains, the message is
  reported as unanswered rather than handed to the free tier. That is a
  choice: an unmonitored free model should not quietly answer, say, a
  security question. The free tier is only for the budget-exhausted case,
  which always comes with an alert.
- Credits are charged only for calls that succeed, live in memory, and reset
  only when refill_all() is called.

Reading the report lines:
- "answered by X": the model that actually replied, after any detours.
- "failed": models that were tried and did not respond.
- "skipped (over budget)": models the agent could not afford, never called.
- "NO MODEL ANSWERED": nothing replied; the report says so instead of
  pretending a reply happened.
- "BREAKER OPEN": the agent is out of credits for the day.

Design decisions, and why:
- Fallback chains cross providers. A single company's outage, rate limit or
  billing problem should slow an agent down, not stop it.
- The report names every detour. A fallback that quietly answers with a
  weaker model looks exactly like success; the only defence is to say, on
  every line, which model answered and which were passed over.
- "Failed" and "skipped" are different facts. Failed means a model was
  tried and did not respond (an availability problem). Skipped means it was
  never tried because the agent could not afford it (a budget decision).
- The budget is checked before any call is made, so an agent that has run
  out costs nothing further, however many messages arrive.
- Failures are not charged. In the real world some providers do bill failed
  or partial calls; the demo leaves that out to keep the arithmetic simple.
- Nothing here routes to a top reasoning model. Choosing when a problem is
  worth the most expensive model is left to a person.

Run: python3 examples/router.py   (standard library only, Python 3.8+)
"""

# === Imports ===
# Only the standard library is used, so the demo runs anywhere Python does.
# random drives the fake outages; seeding it in main() makes runs repeatable.
import random

# dataclass keeps the ledger class short; field(default_factory=...) gives
# each ledger its own dictionary (a plain `= {}` default is rejected).
from dataclasses import dataclass, field


# === 1. Classification ===
# What kind of message is this? Everything downstream depends on the answer:
# a wrong category sends the message to the wrong agent and the wrong models,
# which is why the real Hub spends a model call on this step.
#
# Checked in order; the first category with a matching keyword wins, so the
# specific categories (security, code) come before the general ones. A
# message mentioning both "python" and "leak" is treated as security,
# because missing a security event costs more than misfiling a code question.
CATEGORY_KEYWORDS = {
    # Threat-shaped words: these go to the read-only security agent.
    "security": ["breach", "leak", "intrusion", "suspicious", "ssh"],
    # Programming words: these go to the code-specialized agent.
    "code": ["bug", "function", "python", "traceback", "refactor"],
    # Server chores: routine enough that the Hub keeps them.
    "ops": ["restart", "deploy", "disk", "server", "backup"],
    # Quick factual questions: cheap, so the Hub answers them.
    "lookup": ["weather", "when", "where", "who"],
    # Small talk: the cheapest model is plenty.
    "trivial": ["hi", "thanks", "time"],
}

# Anything with no keyword at all is an ordinary request for the Hub.
DEFAULT_CATEGORY = "simple"


# === 2. Routing ===
# Who handles it? Everyday work stays with the Hub; specialists only see
# their own category, which keeps their (pricier) models for the work they
# are actually better at.
#
# There is deliberately no deep-reasoning agent here: in the real swarm it is
# invoked by hand, never routed to automatically. Auto-routing to the most
# expensive model cost more than it returned.
CATEGORY_TO_AGENT = {
    # The four everyday categories all stay with the dispatcher.
    "trivial": "hub",  # small talk
    "simple": "hub",  # no keyword matched
    "lookup": "hub",  # quick facts
    "ops": "hub",  # server chores
    # Specialists get exactly one category each.
    "code": "code",  # programming
    "security": "security",  # threats, read-only review
}

# Every category the classifier can return must have an owner. Checking once,
# when the module loads, turns a future typo into an immediate, obvious error
# instead of a crash on whichever message first hits the missing category.
assert set(CATEGORY_KEYWORDS) | {DEFAULT_CATEGORY} <= set(CATEGORY_TO_AGENT), \
    "every category needs an agent in CATEGORY_TO_AGENT"

# Fallback chains: (provider, model, credits per successful call), tried in
# order. Chains cross providers so one provider's outage cannot stop an agent.
# Provider and model names are placeholders, not real products; the costs are
# relative, chosen only so that budgets visibly run down during the demo.
FALLBACK_CHAINS = {
    # Hub: two cheap models from different providers before anything pricier.
    "hub": [
        ("provider-a", "small-fast", 1),  # first choice
        ("provider-b", "small-fast", 1),  # same tier, another provider
        # Last resort, three times the price of the first two.
        ("provider-c", "mid-tier", 3),  # third provider
    ],
    # Code: the specialist first, then cheaper general models. Once the
    # budget is low, the specialist is skipped and the report says so,
    # rather than quietly downgrading.
    "code": [
        ("provider-c", "code-specialized", 5),  # best at code, priciest
        ("provider-c", "general", 3),  # cheaper, same provider
        # A different provider at the end, so one outage is never fatal.
        ("provider-a", "small-fast", 1),  # cheapest, other provider
    ],
    # Security: cheap triage first; stronger models only if the cheap one is
    # down. (Escalating BECAUSE an event looks suspicious is a different
    # mechanism; it is the intended direction but is not modeled here.)
    "security": [
        ("provider-b", "triage", 1),  # reads every event cheaply
        ("provider-a", "strong", 4),  # fallback, provider A
        ("provider-c", "strong", 4),  # fallback, provider C
    ],
}

# Where an agent lands once its paid budget is gone. It has no cost, so it can
# never overspend; it is used only together with an alert.
FREE_TIER = ("provider-free", "free-tier")


class ModelUnavailable(Exception):
    """Stands in for any real API failure: timeout, rate limit, outage."""
    # One error type keeps the demo simple. A real client would tell a rate
    # limit (wait and retry) apart from an outage (move on immediately).


def classify(message: str) -> str:
    """Return the category for a message; DEFAULT_CATEGORY if nothing matches."""
    # Lowercase and strip punctuation so "Bug?" and "bug" are the same word.
    # Exact word matching is crude ("bugs" will not match "bug"); that is
    # acceptable for a stand-in and is why the real system uses a model.
    message_words = {word.strip("?!.,:;") for word in message.lower().split()}
    # Walk the categories in priority order and stop at the first match.
    for category_name, keywords in CATEGORY_KEYWORDS.items():
        # One matching keyword is enough to claim the message.
        if any(keyword in message_words for keyword in keywords):
            return category_name
    # Nothing matched: an ordinary request.
    return DEFAULT_CATEGORY


def call_model(provider: str, model_name: str, message: str, failure_rate: float) -> str:
    """Fake model call: raises ModelUnavailable with probability failure_rate."""
    # Each call fails independently. Real outages are often provider-wide,
    # which is why the chains spread models across providers.
    if random.random() < failure_rate:
        raise ModelUnavailable(f"{provider}/{model_name} did not respond")
    # A successful "reply". The demo reports which model answered, not the text.
    return f"[{provider}/{model_name}] reply to {message!r}"


# === 3. Spend cap ===
# The cap exists to catch bugs, not to ration normal use. A loop that re-asks
# the same question hundreds of times is the failure it guards against: it
# runs out of credits for the day instead of running up a bill.
@dataclass
class CreditLedger:
    """Remaining daily credits per agent. Agents start with daily_budget."""

    # Credits each agent starts the day with.
    daily_budget: int = 10
    # Credits left per agent; an agent appears here the first time it spends.
    remaining: dict = field(default_factory=dict)

    def balance(self, agent_name: str) -> int:
        """Credits left for an agent (a full budget the first time it is seen)."""
        # setdefault creates the agent's entry with a full budget on first use,
        # so new agents need no setup step.
        return self.remaining.setdefault(agent_name, self.daily_budget)

    def charge(self, agent_name: str, cost: int) -> None:
        """Deduct the cost of one successful call."""
        # A negative cost would quietly ADD credits, defeating the cap.
        if cost < 0:
            raise ValueError("cost cannot be negative")
        # Only successful calls are charged; failed calls cost nothing here.
        self.remaining[agent_name] = self.balance(agent_name) - cost

    def refill_all(self) -> None:
        """Start a new day: every agent gets its full budget back."""
        # Forgetting all balances means balance() hands out full budgets again.
        self.remaining.clear()


def handle(message: str, ledger: CreditLedger, failure_rate: float = 0.3) -> str:
    """Classify, route and answer one message; return a one-line report."""
    # The three ideas run in order: classify, check the budget, then walk the
    # fallback chain until a model answers or the chain runs out.
    category_name = classify(message)
    # Look up the agent that owns this category (always present; see assert).
    agent_name = CATEGORY_TO_AGENT[category_name]
    # That agent's ordered list of models to try.
    chain = FALLBACK_CHAINS[agent_name]
    # Every report line starts with category and agent, padded into columns.
    prefix = f"{category_name:>8} -> {agent_name:<8}"

    # Breaker: if even the cheapest model is unaffordable, call no paid model.
    # Checking before the loop means a broke agent costs nothing at all.
    cheapest_cost = min(cost for _, _, cost in chain)
    if ledger.balance(agent_name) < cheapest_cost:
        # In the real swarm this is a free model plus an alert to a human;
        # here both are only described, and the line says so.
        free_provider, free_model = FREE_TIER
        return (f"{prefix} BREAKER OPEN: budget exhausted, answered by "
                f"{free_provider}/{free_model} (simulated); alert would fire (simulated)")

    # Track every detour separately, so the report can tell "too expensive"
    # apart from "broken". Lumping them together hides silent downgrades.
    skipped_models = []  # over budget, never called
    failed_models = []   # called, raised ModelUnavailable
    # Try the agent's models in priority order.
    for provider, model_name, cost in chain:
        # The label used in reports, e.g. "provider-c/general".
        model_label = f"{provider}/{model_name}"
        # Too expensive right now: record it and move on without calling it.
        if ledger.balance(agent_name) < cost:
            skipped_models.append(model_label)
            continue
        # Attempt the call; a failure sends us on to the next model.
        try:
            call_model(provider, model_name, message, failure_rate)
        except ModelUnavailable:
            failed_models.append(model_label)
            continue
        # Success: charge only for the call that worked, then report who
        # answered, what it cost, what is left, and any detours on the way.
        ledger.charge(agent_name, cost)
        return (f"{prefix} answered by {model_label}, cost {cost}, "
                f"left {ledger.balance(agent_name)}"
                f"{describe_detours(skipped_models, failed_models)}")

    # Every model was either down or unaffordable. Say so; don't fake success.
    return f"{prefix} NO MODEL ANSWERED{describe_detours(skipped_models, failed_models)}"


def describe_detours(skipped_models: list, failed_models: list) -> str:
    """Format the models passed over on the way to an answer ('' if none)."""
    # Build the note from whichever kinds of detour actually happened.
    parts = []
    # Models never tried because the agent could not afford them.
    if skipped_models:
        parts.append("skipped (over budget): " + ", ".join(skipped_models))
    # Models that were tried and did not respond.
    if failed_models:
        parts.append("failed: " + ", ".join(failed_models))
    # A clean first-try answer gets no note at all.
    return f" ({'; '.join(parts)})" if parts else ""


# === Demo ===
# A mix of everyday and technical messages. The run of code requests at the
# end drains the code agent's budget on purpose, so every outcome appears:
# clean answers, failovers, a skipped specialist, an unanswered message, and
# finally the breaker opening.
SAMPLE_MESSAGES = [
    "hi thanks",  # small talk: Hub, first model answers
    "what's the weather tomorrow",  # lookup: Hub, after a failover
    "restart the backup server",  # ops: stays with the Hub
    "suspicious ssh login from a new country",  # security: cheap triage
    "fix this python traceback",  # code: first of six code requests
    "refactor this function",  # code: budget keeps falling
    "another bug in the parser",  # code: specialist now unaffordable
    "one more bug please",  # code: answered by a cheaper model
    "yet another python bug",  # code: last credit spent
    "final traceback today",  # code: breaker opens
]


def main() -> None:
    """Run the sample messages with a fixed seed so the output is reproducible."""
    # The fixed seed puts the fake outages in the same places every run, which
    # is what lets the tests compare against expected_output.txt.
    random.seed(7)
    # One shared ledger for the whole run, as in a single day of real use.
    ledger = CreditLedger(daily_budget=10)
    # Handle each message in turn and print its one-line report.
    for message in SAMPLE_MESSAGES:
        print(handle(message, ledger))


# Run the demo only when this file is executed directly, not when the tests
# import it.
if __name__ == "__main__":
    main()
