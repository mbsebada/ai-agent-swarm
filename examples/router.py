#!/usr/bin/env python3
# The line above ("shebang") tells the operating system to run this file with
# Python 3 when it is executed directly, e.g. `./router.py`.
"""
router.py — a small, runnable sketch of the three ideas behind the AI Agent Swarm.

WHAT IT DOES
    1. CLASSIFY: looks at an incoming message and sorts it into a category
       ("trivial", "code", "security", ...).
    2. ROUTE: each category maps to one agent, and each agent has a
       FALLBACK CHAIN — an ordered list of models from different providers.
       If the first model fails, the next one is tried.
    3. CIRCUIT BREAKER: every agent has a daily credit budget. If an agent
       burns through it (for example a bug sends it into a loop), it stops
       spending on paid models and drops to the free tier instead.

WHY IT EXISTS
    The real swarm is private: it holds API keys and personal data. This file
    shows the design without any of that. It makes NO network calls — the
    "models" below are fake functions that sometimes fail on purpose, so you
    can watch failover happen.

INPUTS / OUTPUTS
    No inputs. Run it with `python3 examples/router.py` and it prints how a
    handful of sample messages get classified, routed and paid for.
    Standard library only; Python 3.8 or newer.

HOW TO READ THE OUTPUT
    Each printed line is one message. Left to right it shows:
      category   what classify() decided the message is about
      -> agent   which agent CATEGORY_TO_AGENT sent it to
      cost N     credits charged for the call that succeeded
      left N     credits that agent still has today
      (failed over from ...)   providers that failed first, if any
    A line saying BREAKER OPEN means the agent ran out of credits and the
    message was answered by the free tier instead, with an alert raised.
    A line saying ALL PROVIDERS FAILED means every model in the chain was
    down or unaffordable; the swarm says so instead of pretending it worked.

THINGS TO TRY
    - Change failure_rate in handle() from 0.3 to 0.9 and run it again:
      you will see far more failovers, and some ALL PROVIDERS FAILED lines.
    - Change daily_budget from 10 to 3 and the breaker opens much sooner.
    - Change random.seed(7) to another number for a different outage pattern.
    - Add a keyword to CATEGORY_KEYWORDS and watch a message change agents.

HOW THIS MAPS TO THE REAL SWARM
    classify()        the Hub's classification step (a model, not keywords)
    FALLBACK_CHAINS   each agent's configured model list, across providers
    CreditLedger      the daily credit system that refills every morning
    BREAKER OPEN      the "bankruptcy" fallback plus an alert to my phone
    Missing on purpose: the deep-reasoning agent, which is never routed to
    automatically — a human decides when a problem is worth the top model.

GLOSSARY (symbols used throughout)
    #            starts a comment; Python ignores everything after it on the line
    def          defines a function (a named, reusable block of steps)
    ->           in a function header, says what type the function returns
    dict         a lookup table: key -> value
    tuple        a fixed, ordered group of values, written (a, b, c)
    f"...{x}"    an "f-string": text with the value of x dropped in
    !r           inside an f-string: show the value with quotes around it
    :>8 / :<8    inside an f-string: pad to 8 characters, right / left aligned

THE MAIN VARIABLES, AND WHAT EACH ONE HOLDS
    CATEGORY_KEYWORDS  dict  category name -> words that signal it
    CATEGORY_TO_AGENT  dict  category name -> agent that handles it
    FALLBACK_CHAINS    dict  agent name -> ordered list of models to try
    FREE_TIER          tuple the model used when an agent's budget is gone
    ledger             CreditLedger  how many credits each agent has left
"""

# === Imports =================================================================
# "import" loads ready-made tools that ship with Python. Nothing here needs
# installing: both come from Python's built-in standard library.
# No network, file or API libraries are imported, which is how you can tell
# at a glance that this demo never talks to the outside world.
# random: used to make the fake models fail some of the time, like real APIs do.
import random  # standard library: random numbers

# dataclass / field: a shortcut for writing small classes that mainly hold data;
# Python writes the boring setup code (the __init__ method) for us.
from dataclasses import dataclass, field  # standard library: data-holding classes


# === 1. Classification =======================================================
# Classification answers "WHAT KIND of message is this?". Everything after
# it depends on getting this right, which is why the real Hub uses a model
# for it. A wrong category sends the message to the wrong agent and model.
# CATEGORY_KEYWORDS (dict of str -> list of str) — for each category, words
# that suggest a message belongs in it. The real Hub uses a model to classify;
# keywords keep this example deterministic (same answer every time) and free.
# Order matters: Python dicts keep insertion order, and the FIRST category
# whose keyword matches wins — so specific categories go before general ones.
CATEGORY_KEYWORDS = {  # open the lookup table
    # Security first: a "suspicious ssh login" must never be treated as ops.
    "security": ["breach", "leak", "intrusion", "suspicious", "ssh"],  # checked 1st
    # Code next: programming words go to the code-specialized agent.
    "code": ["bug", "function", "python", "traceback", "refactor"],  # checked 2nd
    # Ops: running the machines themselves.
    "ops": ["restart", "deploy", "disk", "server", "backup"],  # checked 3rd
    # Lookup: quick factual questions.
    "lookup": ["weather", "when", "where", "who"],  # checked 4th
    # Trivial: small talk the cheapest model can answer.
    "trivial": ["hi", "thanks", "time"],  # checked last
# Closing brace: the end of the CATEGORY_KEYWORDS table.
}  # end of the table


# `def` starts a function. `message: str` says it expects text; `-> str`
# says it gives text back. EXAMPLE: classify("fix this bug") -> "code".
def classify(message: str) -> str:  # takes text, returns a category name
    """Return the category name for a message ("simple" if nothing matches)."""
    # lowered_words (set of str) — the message's words in lowercase.
    # .lower() makes "Bug" and "bug" the same; .split() breaks on spaces;
    # .strip("?!.,") removes punctuation from each word's ends so "bug?"
    # still matches "bug". The {... for ...} form builds a set (no duplicates).
    lowered_words = {word.strip("?!.,") for word in message.lower().split()}  # set of cleaned words
    # Loop over each category, in the priority order defined above.
    # .items() hands back (key, value) pairs: here (category_name, keywords).
    for category_name, keywords in CATEGORY_KEYWORDS.items():  # one category per pass
        # any(...) is True as soon as ONE keyword is among the message's words.
        if any(keyword in lowered_words for keyword in keywords):  # any keyword present?
            # First match wins: stop looking and report this category.
            return category_name  # first match wins
    # No keyword matched anywhere: treat it as an ordinary request.
    return "simple"  # the default category


# === 2. Routing and fallback chains ==========================================
# Routing answers "WHO handles this?"; the fallback chain answers "WITH
# WHICH MODEL, and what if that model is down?".
# CATEGORY_TO_AGENT (dict of str -> str) — which agent handles each category.
# There is deliberately no "deep reasoning" entry: in the real swarm that
# agent is invoked by hand only, never routed to automatically.
CATEGORY_TO_AGENT = {  # open the routing table
    # Everything everyday stays with the Hub (the dispatcher).
    "trivial": "hub",  # small talk -> Hub
    # A message with no keywords at all is "simple" and stays with the Hub.
    "simple": "hub",  # ordinary requests -> Hub
    # Quick factual questions are cheap, so the Hub answers them itself.
    "lookup": "hub",  # quick facts -> Hub
    # Server chores also stay with the Hub; no specialist needed.
    "ops": "hub",  # machine chores -> Hub
    # Specialists get only their own category.
    "code": "code",  # programming -> code agent
    # Anything security-flavoured goes to the read-only watchdog.
    "security": "security",  # threats -> security agent
# Closing brace: the end of the CATEGORY_TO_AGENT table.
}  # end of the table

# FALLBACK_CHAINS (dict of str -> list of tuples) — for each agent, the
# models to try IN ORDER. Each tuple is (provider, model_tier, cost):
#   provider   — which company runs the model; chains cross companies so
#                one company's outage can't take an agent down
#   model_tier — a description of the model, not a real model name
#   cost       — credits charged per successful call (made-up, relative only)
FALLBACK_CHAINS = {  # open the chains table
    # Hub: cheap and fast first; a mid-tier model only as the last resort.
    "hub": [  # Hub's chain
        # Try 1: the cheapest small model, from company A.
        ("provider-a", "small fast model", 1),  # cheap model from company A
        # Try 2: the same size of model from a DIFFERENT company (B), in case A is down.
        ("provider-b", "small fast model", 1),  # same tier, different company
        # Try 3: a stronger, pricier model from a third company (C).
        ("provider-c", "mid-tier model", 3),  # pricier last resort
    # `],` closes the Hub's list; the comma separates it from the next entry.
    ],  # end of this chain
    # Code: the specialist first, then general models from other providers.
    "code": [  # code agent's chain
        # Try 1: the model trained specifically for code (best, but costs most).
        ("provider-c", "code-specialized model", 5),  # best for code, most expensive
        # Try 2: a general model, cheaper, from the same company.
        ("provider-c", "general mid-tier model", 3),  # same company, cheaper model
        # Try 3: a small model from another company, so a C outage isn't fatal.
        ("provider-a", "small fast model", 1),  # cheap model from company A
    # End of the code agent's list.
    ],  # end of this chain
    # Security: cheap triage on every event; strong models are the fallback.
    # (The October 2026 lesson: not a premium model reading every empty log.)
    "security": [  # security agent's chain
        # Try 1: a cheap model that reads every event and flags anything odd.
        ("provider-b", "cheap fast triage model", 1),  # reads every event cheaply
        # Try 2: a strong model from company A, used only if Try 1 is down.
        ("provider-a", "strong mid-tier model", 4),  # escalation, company A
        # Try 3: a strong model from company C, the last line of defence.
        ("provider-c", "strong mid-tier model", 4),  # escalation, company C
    # End of the security agent's list.
    ],  # end of this chain
# Closing brace: the end of the FALLBACK_CHAINS table.
}  # end of the table

# FREE_TIER (tuple of provider, model_tier, cost) — where an agent lands when
# its paid budget is gone. Cost 0, so it can never overspend.
FREE_TIER = ("provider-free", "free-tier model", 0)  # costs nothing


# `class X(Exception)` creates a new kind of error that `except X` can catch.
# Real APIs fail in many ways (timeouts, rate limits, outages); one error
# type stands in for all of them here.
class ModelUnavailable(Exception):  # a custom error type
    """Raised by a fake model call to simulate an outage or rate limit."""
    # An Exception subclass is a custom error type; `raise` throws it and a
    # matching `except` elsewhere catches it. No body needed beyond this.


# The fake "API call". failure_rate is a fraction: 0.3 means fail 30% of the time.
# EXAMPLE: call_model("provider-a", "small fast model", "hi", 0.0) always succeeds.
def call_model(provider: str, model_tier: str, message: str, failure_rate: float) -> str:  # fake API call
    """Pretend to call a model; fails at random. Returns the fake reply text."""
    # random.random() returns a number from 0.0 up to (not including) 1.0.
    # If it lands below failure_rate (e.g. 0.3 = 30% of the time) we fake
    # an outage by raising the error, exactly as a real API might fail.
    if random.random() < failure_rate:  # roll the dice
        # raise = stop this function now and hand the error to the caller.
        raise ModelUnavailable(f"{provider} is not responding")  # simulate an outage
    # Otherwise "succeed": build a reply showing who answered.
    return f"[{provider} / {model_tier}] handled: {message!r}"  # simulated success


# === 3. Credit circuit breaker ===============================================
# WHY A "CIRCUIT BREAKER": in a house, a breaker cuts the power when
# something draws far too much current, before it starts a fire. Here it
# cuts paid model calls when an agent spends far more than a normal day,
# which almost always means a bug (a loop re-asking the same question)
# rather than real work. The budget is not there to ration normal use.
# @dataclass (a "decorator") tells Python to auto-generate the setup code for
# the class below from the fields listed in it.
@dataclass  # auto-generate the setup code
# `class` defines a new type of object; CreditLedger is our budget book.
class CreditLedger:  # the budget book
    """Tracks each agent's remaining daily credits."""

    # daily_budget (int) — credits every agent starts each day with.
    daily_budget: int = 10  # default: 10 credits a day
    # remaining (dict of str -> int) — credits left per agent right now.
    # field(default_factory=dict) gives EACH ledger its own fresh empty dict;
    # a plain `= {}` would make every ledger share one dict, a classic bug.
    remaining: dict = field(default_factory=dict)  # starts empty

    # A "method" is a function that belongs to a class; `self` is the ledger itself.
    # EXAMPLE: a brand-new ledger's balance("hub") is 10.
    def balance(self, agent_name: str) -> int:  # read a balance
        """Return credits left for an agent (a full budget if never seen)."""
        # setdefault: if agent_name isn't in the dict yet, insert it with a
        # full budget; either way, return the current value.
        return self.remaining.setdefault(agent_name, self.daily_budget)  # full budget on first sight

    # EXAMPLE: charge("hub", 3) when the Hub has 10 leaves it with 7.
    def charge(self, agent_name: str, cost: int) -> None:  # spend credits
        """Subtract the cost of one call from the agent's balance."""
        # Read the current balance, subtract the cost, store the result.
        self.remaining[agent_name] = self.balance(agent_name) - cost  # new balance

    # Not used in the demo; the real swarm runs this once each morning.
    def refill_all(self) -> None:  # daily reset
        """New day: every agent gets its full budget back."""
        # Emptying the dict means balance() re-creates full budgets on demand.
        self.remaining.clear()  # forget all balances


# The main pipeline. `failure_rate: float = 0.3` is a DEFAULT: if the caller
# doesn't pass a value, 0.3 is used.
# EXAMPLE: handle("hi", ledger) -> " trivial -> hub      cost 1, left 9"
def handle(message: str, ledger: CreditLedger, failure_rate: float = 0.3) -> str:  # the whole pipeline
    """Classify, route and answer one message. Returns a one-line report."""
    # The three ideas run in order: classify, check the budget, then try
    # models down the fallback chain until one answers.
    # Step 1: decide what kind of message this is.
    category_name = classify(message)  # e.g. "code"
    # Step 2: look up which agent owns that kind of message.
    agent_name = CATEGORY_TO_AGENT[category_name]  # e.g. "code"

    # --- Circuit breaker check, BEFORE spending anything --------------------
    # cheapest_cost (int) — the least any model in this agent's chain costs.
    # `for _, _, cost in ...` unpacks each tuple; `_` means "ignore this part".
    cheapest_cost = min(cost for _, _, cost in FALLBACK_CHAINS[agent_name])  # smallest price in the chain
    # If the agent can't afford even its cheapest model, the breaker "opens".
    if ledger.balance(agent_name) < cheapest_cost:  # broke?
        # Unpack the free-tier tuple; the cost (0) isn't needed here.
        provider, model_tier, _ = FREE_TIER  # unpack the free model
        # Answer for free instead of spending more.
        reply = f"[{provider} / {model_tier}] handled: {message!r}"  # free answer
        # In the real swarm this also sends an alert so a human checks WHY
        # the budget ran out — usually a loop or a bug, not real demand.
        return f"{category_name:>8} -> {agent_name:<8} BREAKER OPEN, free tier. ALERT sent. {reply}"  # breaker report

    # --- Walk the fallback chain until one model answers --------------------
    # This is the failover: models are tried in the order listed in
    # FALLBACK_CHAINS. The first one that answers wins; a failure or an
    # unaffordable model just moves us one step down the list.
    # failures (list of str) — providers that failed on this message, so the
    # report can show the failover that happened.
    failures = []  # starts empty
    # Loop over each model in the agent's chain, in priority order.
    for provider, model_tier, cost in FALLBACK_CHAINS[agent_name]:  # try models in order
        # Skip any model this agent can no longer afford.
        if ledger.balance(agent_name) < cost:  # too expensive now?
            # continue = jump straight to the next model in the list.
            continue  # next model
        # try/except: attempt the call; if it raises ModelUnavailable, the
        # except block runs instead of the program crashing.
        try:  # attempt the call
            # reply is unused in the report line but shows a real call's shape.
            reply = call_model(provider, model_tier, message, failure_rate)  # may raise
        # `except` runs only if the `try` block above raised ModelUnavailable.
        except ModelUnavailable:  # that provider failed
            # This provider failed: remember it, then try the next model.
            failures.append(provider)  # remember who failed
            # Skip the success code below and go back to the top of the loop.
            continue  # next model
        # Success: charge ONLY for the call that actually worked.
        ledger.charge(agent_name, cost)  # pay for this call
        # failed_note (str) — empty if the first model answered, otherwise a
        # note listing the providers it fell back past. ', '.join(...) glues
        # list items into one string with commas between them.
        failed_note = f" (failed over from {', '.join(failures)})" if failures else ""  # optional note
        # Report: category, agent, what it cost, what's left, any failover.
        return (  # build the report line
            # Two f-strings side by side inside ( ) are glued into one string.
            f"{category_name:>8} -> {agent_name:<8} cost {cost}, "  # first half
            # The second half: remaining balance plus any failover note.
            f"left {ledger.balance(agent_name)}{failed_note}"  # second half
        # Closing parenthesis ends the return value.
        )  # end of report

    # Reaching here means every model in the chain failed or was unaffordable.
    # Say so loudly rather than returning something that looks like success.
    return f"{category_name:>8} -> {agent_name:<8} ALL PROVIDERS FAILED: {', '.join(failures)}"  # loud failure


# === Demo ====================================================================
# Everything above defines the tools; this section actually uses them.
# Run the file and this is the part that prints.
def main() -> None:  # the demo
    """Run a fixed set of sample messages through the router and print results."""
    # A fixed seed makes the "random" outages identical on every run, so the
    # printed output is predictable and can be compared run to run.
    random.seed(7)  # repeatable outages
    # ledger (CreditLedger) — one shared budget book for the whole demo.
    ledger = CreditLedger(daily_budget=10)  # fresh budgets

    # sample_messages (list of str) — a mix of everyday and technical
    # requests. The four code requests drain the code agent's budget on
    # purpose, so you can watch the circuit breaker open at the end.
    sample_messages = [  # demo inputs
        # Small talk -> Hub.
        "hi thanks",  # -> trivial
        # A quick lookup -> Hub.
        "what's the weather tomorrow",  # -> lookup
        # A server chore -> Hub.
        "restart the backup server",  # -> ops
        # A security event -> the security agent.
        "suspicious ssh login from a new country",  # -> security
        # The first of several code requests -> the code agent.
        "fix this python traceback",  # -> code
        # Another code request; the code agent's budget keeps shrinking.
        "refactor this function",  # -> code
        # Another one: still on budget, but only just.
        "another bug in the parser",  # -> code
        # Budget is getting low, so the expensive code model gets skipped.
        "one more bug please",  # -> code (budget runs out)
        # Only the cheapest code model is still affordable for this one.
        "yet another python bug",  # -> code, last credit spent
        # Zero credits left: this one shows BREAKER OPEN and the free tier.
        "final traceback today",  # -> code, breaker opens
    # Closing bracket: the end of the sample list.
    ]  # end of samples
    # WHAT YOU SHOULD SEE (with seed 7): a few "failed over from" notes as
    # fake outages hit; one ALL PROVIDERS FAILED line; the code agent's
    # balance falling 7 -> 4 -> 1 -> 0; and BREAKER OPEN on the last line.
    # The Hub and security agents never come close to their limits, which
    # is the point: the breaker exists to catch a runaway, not normal use.
    # Loop over each sample message and print how it was handled.
    for message in sample_messages:  # one sample per pass
        # handle() does classify -> breaker check -> fallback chain.
        print(handle(message, ledger))  # run and show it


# __name__ equals "__main__" only when this file is run directly
# (python3 router.py), not when another file imports it. That keeps the demo
# from running by surprise if someone reuses these functions.
if __name__ == "__main__":  # run directly?
    # Call the demo function defined above.
    main()  # start the demo
