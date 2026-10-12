# AI Agent Swarm

A multi-agent AI platform with intelligent routing, provider failover, credit-based circuit breakers, and self-healing infrastructure.

## What Is This?

Instead of one chatbot connected to a notes app, this is a **swarm of specialized agents** that classify tasks, route them to the optimal model, fail over across providers, and monitor themselves.

```
You (Chat Channels)
  │
  ▼
┌─────────────────────────────────────────────┐
│  Hub (Dispatcher + daily driver)            │
│  Classifies message → 9 categories          │
│  Answers simple ones, routes the rest       │
└────────┬───────────────────┬────────────────┘
         │                   │
         ▼                   ▼
       Code              Security
     (code tasks)      (read-only scans)

  Deep reasoning: separate agent, invoked by hand only —
  never auto-routed (see "What changed since March")
```

## What Changed Since March (October 2026 update)

The swarm has been running daily since this write-up. Seven months of use changed it:

- **Fewer agents, not more.** It peaked at more specialists (a coach, a trader, a personal assistant, a separate "main" agent). Most got folded into the Hub. Each extra agent was one more thing to monitor, and the Hub handled their jobs fine. Today: 3 routed agents plus 1 manual one.
- **The expensive model came out of automatic routing.** The top reasoning model is now a separate agent I call by hand. Auto-routing to it cost more than it returned; when a problem is genuinely hard, I already know it.
- **A "smarter" security model got reverted the same night.** I tried a premium preview model as the security agent's primary. A second-opinion review killed it: about 5–7x the cost per token, tighter burst rate limits, and preview models can change silently. The worst part is that **fallbacks fire on errors, not on confidently wrong answers**. The better design is cheap triage on every event, escalating to a strong model only when something looks suspicious.
- **Alerts got quieter.** Warnings and info now go to a log instead of my phone. Only critical alerts interrupt me. An alert channel that fires constantly gets ignored, which is worse than no alert.
- **The credit circuit breaker stayed.** It's the one piece that never needed redesign.

**Lesson:** the architecture that survived is the boring one. Cheap default, strong fallback, a human picking when to pay for the best model.

## Architecture

### Agent Swarm

| Agent | Role | Model Tier | Notes |
|-------|------|-----------|-------|
| Hub | Dispatcher + simple tasks | Small fast model | 3 fallbacks across 3 providers |
| Code | Code specialist | Code-specialized model | Restricted filesystem |
| Security | Watchdog | Cheap fast model, strong fallback | Read-only, never modifies |
| Deep reasoning | Hard problems | Top reasoning model | Manual only, not in dispatch |

### Intelligent Routing

Every message is classified into one of 9 categories and routed to the cheapest model that can handle it:

```
trivial  → free tier
simple   → fast mid-tier
lookup   → fast mid-tier
data     → fast mid-tier
ops      → strong mid-tier
code     → code-specialized
security → strong mid-tier
complex  → top reasoning
hardest  → maximum capability
```

The dispatcher and security chains each span all 3 major providers; the code chain spans 2. No single provider outage takes the swarm down.

### Credit Economy (Circuit Breaker)

- Each agent gets a daily credit budget, auto-refilled
- Prevents runaway API costs from rogue loops
- Bankruptcy fallback: Hub switches to free tier + sends alert
- Guard script validates all state writes and auto-backs up

### Infrastructure

```
┌──────────────────────┐     ┌──────────────────────┐
│  Local (Primary)     │◄───►│  VPS (Always-On)     │
│                      │     │                      │
│  Gateway             │     │  Gateway             │
│  AI Agents           │     │  Database + Cache    │
│  Dev CLI             │     │  Workflow Engine     │
│                      │     │  Monitoring          │
│                      │     │  Reverse Proxy       │
│                      │     │  Local LLM           │
└──────────────────────┘     └──────────────────────┘
      Bidirectional delegation via gateways
```

### Monitoring

- Health checks on a short interval, auto-discovering services
- Multiple monitoring probes with instant alerts
- Workflow automations for usage tracking and cost alerts
- Daily backups with retention policies

### Security Posture

- Key-only auth + intrusion detection
- All services behind reverse proxy (zero exposed ports)
- Strict file permissions
- Automated API key rotation
- Bot access restricted to allowlists
- Dedicated read-only security agent with continuous scanning
- Per-agent tool restrictions and execution policies

## Channels

| Channel | Status |
|---------|--------|
| Chat app 1 | Active |
| Chat app 2 | Active |
| Chat app 3 | Active |

## Cost

| Item | Monthly |
|------|---------|
| VPS | ~$12 |
| API usage | Variable (routing optimized) |
| Free-tier model | $0 |
| Search API | ~$25 |
| **Infrastructure total** | **~$37 + API** |

Routing optimization is the cost control. Most messages hit free/cheap models. Expensive models only fire for genuinely complex tasks.

## Design Principles

1. **Route to the cheapest capable model.** Don't waste frontier-model tokens on "what time is it?"
2. **Every chain crosses providers.** No single point of failure.
3. **Circuit breakers, not budgets.** Credit limits exist to catch bugs, not restrict usage.
4. **Security agent is read-only.** An agent that can detect AND fix problems is an agent that can cause problems.
5. **Monitor before you scale.** Add observability before adding complexity.

## Reference Code

The production system is private (it holds keys and personal data). [`examples/router.py`](examples/router.py) is a small, standalone, runnable version of the three core ideas — classify-and-route, cross-provider fallback, and the credit circuit breaker — with no API calls and no dependencies:

```
python3 examples/router.py
```

## Getting Started

1. Start with one agent, one channel, one model
2. Add a second agent with a different specialty + routing
3. Add monitoring and alerting
4. Add provider failover + credit limits

## License

MIT
