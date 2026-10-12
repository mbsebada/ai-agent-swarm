# How `router.py` works, in plain English

`router.py` is a small model of how the swarm decides who answers a message, what happens when an AI service is down, and how spending is capped. It never contacts a real AI service. The "models" in it are pretend, and they fail at random on purpose so you can watch the backups kick in.

Run it from the repository folder:

```
python3 examples/router.py
```

## The three parts

**1. Sorting the message (classify).** The program looks for keywords. "ssh" or "breach" means security, "bug" or "python" means code, "restart" or "backup" means server chores, and so on. Anything with no keyword counts as "simple." The real system uses an AI model for this step. Keywords are a cheap, predictable stand-in for the demo.

**2. Picking who answers (route and fall back).** Each category belongs to one agent:

- the Hub handles everyday messages
- the code agent handles programming
- the security agent handles anything that looks like a threat

Each agent has a backup list of AI models, ordered from first choice to last resort, and spread across different companies. If the first model doesn't answer, the next one is tried. A model the agent can't currently afford is skipped instead of tried.

**3. The spending cap (circuit breaker).** Every agent gets a daily allowance of credits, and a successful answer costs credits. If an agent can't afford even its cheapest model, it stops calling paid models. The message gets a free-tier answer, and an alert is raised so a person can check why the money ran out. Usually the cause is a bug, such as a loop asking the same thing over and over, not real demand. In the demo, both the free answer and the alert are only described, not actually sent.

One choice is deliberate. If every paid model is down while the agent still has money, the program reports that nobody answered. It does not quietly hand the message to the free model. A security question shouldn't get an answer from an unmonitored model just because everything else was busy.

## Reading the output

Each line is one message:

```
    code -> code     answered by provider-c/general, cost 3, left 4 (failed: provider-c/code-specialized)
```

- `code -> code`: the message was sorted as "code" and given to the code agent.
- `answered by provider-c/general`: the model that actually replied.
- `cost 3, left 4`: credits spent on this message, and credits the agent has left today.
- `(failed: ...)`: models that were tried first and didn't respond.
- `(skipped (over budget): ...)`: models that were too expensive to try right now.
- `NO MODEL ANSWERED`: every model was either down or unaffordable.
- `BREAKER OPEN`: the agent is out of credits. The message got a (simulated) free answer, and a (simulated) alert would fire.

The demo uses a fixed random seed, so the pretend outages happen in the same places every run. The exact output is saved in `expected_output.txt`, and the tests check against it.

## Things to try

- In `handle()`, change `failure_rate` from `0.3` to `0.9`. You'll see far more failures and several `NO MODEL ANSWERED` lines.
- In `main()`, change `daily_budget=10` to `3`. The breaker opens much sooner.
- Change `random.seed(7)` to another number for a different pattern of outages. The test comparing against `expected_output.txt` will then fail, which is how you can tell the output changed.
- Add a word to one of the lists in `CATEGORY_KEYWORDS` and watch a message move to a different agent.

## What it leaves out

The real system is private, because it holds keys and personal data. This demo has no network calls, no real model names, no saved state between runs, and no deep-reasoning agent. In the real setup, that agent is only ever called by hand, never picked automatically.

## Running the tests

```
python3 -m unittest discover -s tests -v
```
