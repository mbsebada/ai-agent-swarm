# AI Agent Swarm

Notes and a runnable sketch from running a small multi-agent AI setup every day since March 2026: a dispatcher that answers simple requests itself and hands code and security work to two specialist agents, each backed by models from more than one AI provider.

**The lesson so far: the architecture that survived is the boring one.** A cheap default model, a stronger fallback, and a human deciding when a problem is worth the most expensive model.

Built on [OpenClaw](https://github.com/openclaw/openclaw). The configuration and this demo were written with AI assistance and reviewed by me.

## What Changed Since March

The first version of this write-up (now in [`archive/`](archive/)) described a bigger system than the one that lasted:

- **Fewer agents, not more.** It peaked at more specialists (a coach, a trader, a personal assistant, a separate "main" agent). Most were folded into the Hub. Each extra agent was one more thing to watch, and the Hub handled their jobs fine.
- **The expensive model came out of automatic routing.** The top reasoning model is now a separate agent I call by hand. Routing to it automatically cost more than it returned; when a problem is genuinely hard, I already know it.
- **A "smarter" security model was reverted the same night.** I tried a premium preview model as the security agent's main model. A second-opinion review turned it down: roughly 5 to 7 times the cost per token, tighter burst rate limits, and preview models can change without notice. Most important: **fallbacks fire on errors, not on confidently wrong answers.**
- **Alerts got quieter.** Warnings and routine notices now go to a log. Only critical alerts reach my phone. An alert channel that fires constantly gets ignored.
- **The daily spend cap stayed.** It is the one piece that has not needed a redesign.

## How It Works Today

```
You (chat app)
  │
  ▼
┌─────────────────────────────────────────────┐
│  Hub (dispatcher + daily driver)            │
│  Sorts each message by kind                 │
│  Answers everyday requests itself           │
└────────┬───────────────────┬────────────────┘
         │                   │
         ▼                   ▼
       Code              Security
     (code tasks)      (read-only review)

  Deep reasoning: a separate agent I invoke by hand.
  Nothing is routed to it automatically.
```

| Agent | Handles | Main model | Fallbacks |
|-------|---------|-----------|-----------|
| Hub | Small talk, lookups, everyday requests, server chores | Small, fast model | 3 more, spread across 3 providers |
| Code | Programming tasks | Code-specialized model | General models; the chain spans 2 providers |
| Security | Reviewing events; read-only, never changes anything | Cheap, fast triage model | Stronger models from other providers |
| Deep reasoning | Hard problems, on request | Top reasoning model | Not in automatic routing |

### Routing

The Hub sorts each message by kind and keeps everything it can handle: small talk, quick lookups, ordinary requests, and server chores. Programming goes to the Code agent; anything security-related goes to the Security agent. No kind of message is routed automatically to the top reasoning model.

Each agent has an ordered list of models. If one fails or times out, the next is tried. The Hub's and Security agent's lists each include models from three providers and the Code agent's from two, so one provider's outage does not stop an agent on its own.

For the Security agent, the stronger models are currently **fallbacks on error only**. Escalating to a stronger model *because an event looks suspicious* is the intended direction, but it is not built yet.

### Daily Spend Cap

- Each agent has a daily credit budget that refills automatically.
- It works like a circuit breaker for runaway loops: if a bug makes an agent call models over and over, it runs out of credits instead of running up a bill.
- When the Hub runs out, it drops to a free model and an alert goes out.

### Infrastructure

```
┌──────────────────────┐     ┌──────────────────────┐
│  Home computer       │◄───►│  Rented server (VPS) │
│                      │     │                      │
│  Gateway             │     │  Gateway             │
│  AI agents           │     │  Database + cache    │
│                      │     │  Workflow engine     │
│                      │     │  Monitoring          │
│                      │     │  Reverse proxy       │
│                      │     │  Local LLM (Ollama)  │
└──────────────────────┘     └──────────────────────┘
       The two gateways can hand work to each other
```

### Monitoring

- Uptime checks with alerts for the services on the server
- Workflow automations for usage tracking and cost alerts
- Regular backups
- Critical alerts notify me; warnings and routine notices go to a log

### Security

- The server's firewall blocks everything by default. From the internet, only the web ports (through the reverse proxy) and SSH are reachable; the database, workflow engine, local LLM and other internal services are not.
- SSH uses keys, not passwords.
- API keys are rotated with a script per service, run by hand whenever a key may have been exposed.
- Chat bots answer only approved accounts (an allowlist, or a one-time pairing approval for new users).
- The Security agent is read-only: it can flag problems but cannot change anything.
- Each agent has its own tool restrictions.

### Cost

Fixed costs are a small server and the AI subscriptions I already pay for. I have not yet broken out how much of my API spend comes from this system specifically, so I am not quoting a number.

## Design Principles

1. **Use the cheapest model that does the job.** Don't spend top-model tokens on "what time is it?"
2. **Spread each agent's models across providers.** One company's outage should not stop an agent.
3. **A spend cap catches bugs; it is not there to ration normal use.**
4. **The security agent is read-only.** An agent that can both detect and fix problems is an agent that can cause them.
5. **Add monitoring before adding complexity.**

## Reference Code

The real system is private: it holds API keys and personal data. This repo has a small, standalone version of the core ideas instead:

- [`examples/router.py`](examples/router.py) — runnable sketch of sorting messages, model fallback, and the daily spend cap. No network calls, no dependencies: `python3 examples/router.py`
- [`examples/HOW_IT_WORKS.md`](examples/HOW_IT_WORKS.md) — a plain-English walkthrough of the code
- [`tests/`](tests/) — checks that the demo behaves as described

## Archive

[`archive/`](archive/) holds the original March 2026 write-up. It is kept for the record and is no longer accurate.

## License

MIT
