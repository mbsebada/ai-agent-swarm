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

The demo's ten lines, one by one (seed 7, ten credits per agent):
1. "hi thanks": small talk, the Hub's first model answers. Hub left 9.
2. "what's the weather tomorrow": the first Hub model fails, the second
   (another provider) answers. Hub left 8.
3. "restart the backup server": ops stays on the Hub; same failover. Left 7.
4. "suspicious ssh login...": the security agent's cheap triage model
   answers on the first try. Security left 9.
5. "fix this python traceback": the code specialist fails; the general
   model answers for 3. Code left 7.
6. "refactor this function": same pattern. Code left 4.
7. "another bug in the parser": the specialist (5) is now too expensive and
   is skipped; the two affordable models both fail. NO MODEL ANSWERED, and
   nothing is charged.
8. "one more bug please": specialist skipped, general answers. Code left 1.
9. "yet another python bug": only the cost-1 model is affordable; it
   answers. Code left 0.
10. "final traceback today": zero credits, so the breaker opens and no paid
   model is called.
The Hub and security agents never get near their limits, which is the
point: the cap is there to catch a runaway, not to ration a normal day.

Changing things safely:
- Every number that shapes the demo lives in one of four tables near the
  top (keywords, category owners, chains, free tier) or in main() (seed and
  budget). Change those, not the logic, to explore.
- The tests (tests/test_router.py) pin the behavior down. If a change alters
  the demo's output on purpose, regenerate expected_output.txt by running
  this file and saving what it prints; if a change alters it by accident,
  the tests say so.
- The assert under CATEGORY_TO_AGENT stops the program at startup if a new
  keyword category has no agent, so that mistake cannot reach a message.

Why the seed is fixed:
- Random outages make a demo vivid but a test impossible. Seeding the
  random number generator replays the same "random" outages every run, so
  the printed lines are identical each time and can be checked against a
  saved copy. Change the seed in main() to see a different day.
- The tests that need specific outcomes (every model down, one failure then
  a success) do not rely on the seed at all; they replace call_model() with
  a stand-in that fails exactly when told to.

What the demo deliberately does NOT show:
- Real model names, prices or API calls: everything is a placeholder.
- The deep-reasoning agent: in the real system a person invokes it.
- Saved state: credits reset every time the file runs.
- Concurrency: messages are handled one at a time, in order.

Where each idea lives in this file:
- Classification: CATEGORY_KEYWORDS, DEFAULT_CATEGORY and classify().
- Routing: CATEGORY_TO_AGENT and FALLBACK_CHAINS.
- Spend cap: CreditLedger and the breaker check at the top of handle().
- Reporting: the return lines in handle() and describe_detours().
- Demo: SAMPLE_MESSAGES and main(), at the bottom.
- Errors: ModelUnavailable, the one failure the fallback loop catches.
- Checks: the assert under CATEGORY_TO_AGENT, run once at startup.
- Tests: tests/test_router.py, outside this file.

Terms used throughout:
- agent: a worker with its own job (Hub, code, security) and its own models.
- provider: the company that runs a model. Spreading models across
  providers is what makes failover meaningful.
- model: one AI model at one price; listed here by a placeholder name.
- chain: an agent's ordered list of models, first choice to last resort.
- credit: the demo's unit of spend; each successful call costs some.
- breaker: the check that stops paid calls once an agent's credits are gone.

Worked example: the message "one more bug please" with 4 credits left.
1. classify() finds "bug" and returns "code".
2. CATEGORY_TO_AGENT sends it to the code agent.
3. The cheapest code model costs 1 and 4 >= 1, so the breaker stays closed.
4. The specialist costs 5 and 4 < 5, so it is skipped, not called.
5. The general model costs 3 and is affordable, so it is called.
6. It answers; 3 credits are charged, leaving 1.
7. The report reads: answered by provider-c/general, cost 3, left 1,
   (skipped (over budget): provider-c/code-specialized).
The skip appears in the report on purpose: a weaker model answered, and the
line says so instead of letting the downgrade pass silently.

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

What a production version would add (and the real system mostly has):
- A model-based classifier instead of keywords, with a confidence score so
  uncertain messages can go to a stronger model.
- Budgets that persist across restarts and refill on a schedule.
- Separate handling for rate limits (wait and retry) and outages (move on).
- Charging for failed or partial calls where providers bill for them.
- Real alerts: critical ones to a phone, routine ones to a log.
- Escalation on content (a suspicious event goes to a stronger model even
  when the cheap one is working), which is the planned next step.

Run: python3 examples/router.py   (standard library only, Python 3.8+)
"""

# === Imports ===
# Only the standard library is used, so the demo runs anywhere Python does.
# random drives the fake outages; seeding it in main() makes runs repeatable.
import random  # fake outages

# dataclass keeps the ledger class short; field(default_factory=...) gives
# each ledger its own dictionary (a plain `= {}` default is rejected).
from dataclasses import dataclass, field  # short data classes


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
# Five keyword families in all; anything else falls through to the default.
}

# Anything with no keyword at all is an ordinary request for the Hub.
DEFAULT_CATEGORY = "simple"  # owned by the Hub


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
    # Ordinary requests with no special keywords.
    "simple": "hub",  # no keyword matched
    # Weather, times, who-is questions: one cheap call answers them.
    "lookup": "hub",  # quick facts
    # Restarts, deploys, disk and backup chores.
    "ops": "hub",  # server chores
    # Specialists get exactly one category each.
    "code": "code",  # programming
    # Threat-shaped messages; this agent can flag but never change anything.
    "security": "security",  # threats, read-only review
# Six categories, three agents: the Hub owns four of them.
}

# Every category the classifier can return must have an owner. Checking once,
# when the module loads, turns a future typo into an immediate, obvious error
# instead of a crash on whichever message first hits the missing category.
# The text after the comma is the message shown if a category is ever added
# without an owner.
assert set(CATEGORY_KEYWORDS) | {DEFAULT_CATEGORY} <= set(CATEGORY_TO_AGENT), \
    "every category needs an agent in CATEGORY_TO_AGENT"

# Fallback chains: (provider, model, credits per successful call), tried in
# order. Chains cross providers so one provider's outage cannot stop an agent.
# Provider and model names are placeholders, not real products; the costs are
# relative, chosen only so that budgets visibly run down during the demo.
FALLBACK_CHAINS = {
    # Hub: two cheap models from different providers before anything pricier.
    "hub": [
        # Both cheap models come first, from two different providers.
        ("provider-a", "small-fast", 1),  # first choice
        # If provider A is down, the same size of model from B takes over.
        ("provider-b", "small-fast", 1),  # same tier, another provider
        # Last resort, three times the price of the first two.
        ("provider-c", "mid-tier", 3),  # third provider
    # Three tries, three providers: the Hub survives any single outage.
    ],
    # Code: the specialist first, then cheaper general models. Once the
    # budget is low, the specialist is skipped and the report says so,
    # rather than quietly downgrading.
    "code": [
        # Only the code agent pays for a code-specialized model.
        ("provider-c", "code-specialized", 5),  # best at code, priciest
        # Same provider, lower price: used when the specialist fails or is unaffordable.
        ("provider-c", "general", 3),  # cheaper, same provider
        # A different provider at the end, so one outage is never fatal.
        ("provider-a", "small-fast", 1),  # cheapest, other provider
    # Two providers in this chain, so a provider-c outage still leaves one model.
    ],
    # Security: cheap triage first; stronger models only if the cheap one is
    # down. (Escalating BECAUSE an event looks suspicious is a different
    # mechanism; it is the intended direction but is not modeled here.)
    "security": [
        # Most events are noise, so a cheap model reads them first.
        ("provider-b", "triage", 1),  # reads every event cheaply
        # Used only when triage is down, not because an event looks serious.
        ("provider-a", "strong", 4),  # fallback, provider A
        # A third provider, so security review keeps running through one outage.
        ("provider-c", "strong", 4),  # fallback, provider C
    # Three tries across three providers, like the Hub.
    ],
# Each agent's chain is independent; one agent's failures never touch another's.
}

# Where an agent lands once its paid budget is gone. It has no cost, so it can
# never overspend; it is used only together with an alert.
FREE_TIER = ("provider-free", "free-tier")  # (provider, model)


# The single kind of failure the fallback loop knows how to handle.
class ModelUnavailable(Exception):
    """Stands in for any real API failure: timeout, rate limit, outage."""
    # One error type keeps the demo simple. A real client would tell a rate
    # limit (wait and retry) apart from an outage (move on immediately).


# Step one of handle(): turn free text into one of the known categories.
# Example: classify("suspicious ssh login") returns "security".
def classify(message: str) -> str:
    """Return the category for a message; DEFAULT_CATEGORY if nothing matches."""
    # Lowercase and strip punctuation so "Bug?" and "bug" are the same word.
    # Exact word matching is crude ("bugs" will not match "bug"); that is
    # acceptable for a stand-in and is why the real system uses a model.
    message_words = {word.strip("?!.,:;") for word in message.lower().split()}  # set of cleaned words
    # Walk the categories in priority order and stop at the first match.
    for category_name, keywords in CATEGORY_KEYWORDS.items():  # priority order
        # One matching keyword is enough to claim the message.
        if any(keyword in message_words for keyword in keywords):  # one hit is enough
            # The first category that matches wins; later categories are not checked.
            return category_name
    # Nothing matched: an ordinary request.
    return DEFAULT_CATEGORY  # "simple"


# Pretend to ask one model for an answer. failure_rate=0.3 fails about 30%
# of calls; 1.0 fails every call, which the tests use to force outages.
def call_model(provider: str, model_name: str, message: str, failure_rate: float) -> str:
    """Fake model call: raises ModelUnavailable with probability failure_rate."""
    # Each call fails independently. Real outages are often provider-wide,
    # which is why the chains spread models across providers.
    if random.random() < failure_rate:  # the simulated outage
        # Raising (instead of returning an error value) forces the caller to handle it.
        raise ModelUnavailable(f"{provider}/{model_name} did not respond")
    # A successful "reply". The demo reports which model answered, not the text.
    return f"[{provider}/{model_name}] reply to {message!r}"  # the simulated reply


# === 3. Spend cap ===
# The cap exists to catch bugs, not to ration normal use. A loop that re-asks
# the same question hundreds of times is the failure it guards against: it
# runs out of credits for the day instead of running up a bill.
@dataclass
# One ledger tracks every agent's credits for the day.
class CreditLedger:
    """Remaining daily credits per agent. Agents start with daily_budget."""

    # Credits each agent starts the day with.
    daily_budget: int = 10
    # Credits left per agent; an agent appears here the first time it spends.
    remaining: dict = field(default_factory=dict)

    # Called before every model attempt, so the balance is always current.
    # Example: on a new ledger, balance("hub") returns 10.
    def balance(self, agent_name: str) -> int:
        """Credits left for an agent (a full budget the first time it is seen)."""
        # setdefault creates the agent's entry with a full budget on first use,
        # so new agents need no setup step.
        return self.remaining.setdefault(agent_name, self.daily_budget)  # full budget on first use

    # Called once per successful answer, never for failed attempts.
    # Example: charge("code", 3) on 10 credits leaves 7.
    def charge(self, agent_name: str, cost: int) -> None:
        """Deduct the cost of one successful call."""
        # A negative cost would quietly ADD credits, defeating the cap.
        if cost < 0:  # guard against adding credits
            # Fail loudly: a silent bad charge would corrupt the cap.
            raise ValueError("cost cannot be negative")
        # Only successful calls are charged; failed calls cost nothing here.
        self.remaining[agent_name] = self.balance(agent_name) - cost  # the new balance

    # The real swarm refills budgets once a day; the demo never calls this.
    def refill_all(self) -> None:
        """Start a new day: every agent gets its full budget back."""
        # Forgetting all balances means balance() hands out full budgets again.
        self.remaining.clear()  # every agent back to full


# The whole pipeline for one message. It never raises for an outage: every
# outcome, good or bad, comes back as one readable report line.
def handle(message: str, ledger: CreditLedger, failure_rate: float = 0.3) -> str:
    """Classify, route and answer one message; return a one-line report."""
    # The three ideas run in order: classify, check the budget, then walk the
    # fallback chain until a model answers or the chain runs out.
    category_name = classify(message)  # e.g. "code"
    # Look up the agent that owns this category (always present; see assert).
    agent_name = CATEGORY_TO_AGENT[category_name]  # e.g. "code"
    # That agent's ordered list of models to try.
    chain = FALLBACK_CHAINS[agent_name]  # list of (provider, model, cost)
    # Every report line starts with category and agent, padded into columns.
    prefix = f"{category_name:>8} -> {agent_name:<8}"  # aligned columns

    # Breaker: if even the cheapest model is unaffordable, call no paid model.
    # Checking before the loop means a broke agent costs nothing at all.
    cheapest_cost = min(cost for _, _, cost in chain)  # lowest price in the chain
    # The cheapest model is the least any call could cost; if that is out of
    # reach, the agent is out of money for today.
    if ledger.balance(agent_name) < cheapest_cost:  # out of money for today
        # In the real swarm this is a free model plus an alert to a human;
        # here both are only described, and the line says so.
        free_provider, free_model = FREE_TIER  # the no-cost fallback
        # Report the breaker in place of an answer, clearly marked as simulated.
        return (f"{prefix} BREAKER OPEN: budget exhausted, answered by "
                # The second half of the same report line.
                f"{free_provider}/{free_model} (simulated); alert would fire (simulated)")

    # Track every detour separately, so the report can tell "too expensive"
    # apart from "broken". Lumping them together hides silent downgrades.
    skipped_models = []  # over budget, never called
    # Models that were tried but did not respond.
    failed_models = []   # called, raised ModelUnavailable
    # Try the agent's models in priority order.
    for provider, model_name, cost in chain:  # first choice to last resort
        # The label used in reports, e.g. "provider-c/general".
        model_label = f"{provider}/{model_name}"  # e.g. "provider-c/general"
        # Too expensive right now: record it and move on without calling it.
        if ledger.balance(agent_name) < cost:  # unaffordable right now
            # Record the skip so the report shows the downgrade.
            skipped_models.append(model_label)  # remember the skip
            # Move straight on to the next, cheaper model.
            continue  # next model
        # Attempt the call; a failure sends us on to the next model.
        try:  # attempt the call
            # The fake call; its reply text is not needed, only whether it raised.
            call_model(provider, model_name, message, failure_rate)  # may raise
        # Any outage-style failure lands here.
        except ModelUnavailable:  # this model is down
            # Record which model failed for the report.
            failed_models.append(model_label)  # remember the failure
            # Try the next model in the chain.
            continue  # next model
        # Success: charge only for the call that worked, then report who
        # answered, what it cost, what is left, and any detours on the way.
        ledger.charge(agent_name, cost)  # pay only for success
        # Build the success report: who answered and what it cost...
        return (f"{prefix} answered by {model_label}, cost {cost}, "
                # ...how many credits the agent has left today...
                f"left {ledger.balance(agent_name)}"
                # ...and any models passed over on the way.
                f"{describe_detours(skipped_models, failed_models)}")

    # Every model was either down or unaffordable. Say so; don't fake success.
    return f"{prefix} NO MODEL ANSWERED{describe_detours(skipped_models, failed_models)}"


# Turns the two detour lists into the parenthesized note on a report line.
# Example: (["a/x"], []) becomes " (skipped (over budget): a/x)".
def describe_detours(skipped_models: list, failed_models: list) -> str:
    """Format the models passed over on the way to an answer ('' if none)."""
    # Build the note from whichever kinds of detour actually happened.
    parts = []  # pieces of the note
    # Models never tried because the agent could not afford them.
    if skipped_models:  # any budget skips?
        # Join several skipped models with commas.
        parts.append("skipped (over budget): " + ", ".join(skipped_models))  # skips first
    # Models that were tried and did not respond.
    if failed_models:  # any failures?
        # Join several failed models with commas.
        parts.append("failed: " + ", ".join(failed_models))  # then failures
    # A clean first-try answer gets no note at all.
    return f" ({'; '.join(parts)})" if parts else ""  # empty when no detours


# === Demo ===
# A mix of everyday and technical messages. The run of code requests at the
# end drains the code agent's budget on purpose, so every outcome appears:
# clean answers, failovers, a skipped specialist, an unanswered message, and
# finally the breaker opening.
SAMPLE_MESSAGES = [
    # Everyday messages first: these exercise the Hub.
    "hi thanks",  # small talk: Hub, first model answers
    # The fixed seed makes the first Hub model fail here.
    "what's the weather tomorrow",  # lookup: Hub, after a failover
    # Ops shows that server chores stay with the dispatcher.
    "restart the backup server",  # ops: stays with the Hub
    # One security event, answered by the cheap triage model.
    "suspicious ssh login from a new country",  # security: cheap triage
    # From here on, code requests drain the code agent's ten credits.
    "fix this python traceback",  # code: first of six code requests
    # Second code request: the specialist fails again, general answers.
    "refactor this function",  # code: budget keeps falling
    # Every model the code agent can still afford fails on this one.
    "another bug in the parser",  # code: specialist now unaffordable
    # Only 4 credits left, so the cost-5 specialist is skipped.
    "one more bug please",  # code: answered by a cheaper model
    # The last credit goes to the cheapest code model.
    "yet another python bug",  # code: last credit spent
    # Zero credits: the breaker opens.
    "final traceback today",  # code: breaker opens
# Ten messages in total.
]


# The demo entry point: same ten messages, same seed, same output.
def main() -> None:
    """Run the sample messages with a fixed seed so the output is reproducible."""
    # The fixed seed puts the fake outages in the same places every run, which
    # is what lets the tests compare against expected_output.txt.
    random.seed(7)  # same outages every run
    # One shared ledger for the whole run, as in a single day of real use.
    ledger = CreditLedger(daily_budget=10)  # ten credits per agent
    # Handle each message in turn and print its one-line report.
    for message in SAMPLE_MESSAGES:  # in order, as if over one day
        # Each report is one line; reading them top to bottom tells the day's story.
        print(handle(message, ledger))  # one report line each


# Run the demo only when this file is executed directly, not when the tests
# import it.
if __name__ == "__main__":
    # Start the demo.
    main()  # run the ten messages
