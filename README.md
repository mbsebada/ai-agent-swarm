# AI Agent Swarm

A multi-agent AI platform with intelligent routing, provider failover, credit-based circuit breakers, and self-healing infrastructure.

## What Is This?

Instead of one chatbot connected to a notes app, this is a **swarm of specialized agents** that classify tasks, route them to the optimal model, fail over across providers, and monitor themselves.

```
You (Chat Channels)
  │
  ▼
┌─────────────────────────────────────────────┐
│  Hub (Dispatcher)                           │
│  Classifies message → 9 categories          │
│  Routes to optimal agent + model            │
└────┬────────┬────────┬────────┬─────────────┘
     │        │        │        │
     ▼        ▼        ▼        ▼
  Main      Code    Security   Personal
  (complex) (code)  (scans)    (separate
  reasoning  tasks   read-only  workspace)
```

## Architecture

### Agent Swarm

| Agent | Role | Model Tier | Notes |
|-------|------|-----------|-------|
| Hub | Dispatcher + simple tasks | Free / fast mid-tier | Handles trivial in-house |
| Main | Complex reasoning | Top reasoning model | Multi-provider fallback |
| Code | Code specialist | Code-specialized model | Restricted filesystem |
| Security | Watchdog | Strong mid-tier | Read-only, never modifies |

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

Every fallback chain spans all 3 major providers. No single point of failure.

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
2. **Every chain covers all providers.** No single point of failure.
3. **Circuit breakers, not budgets.** Credit limits exist to catch bugs, not restrict usage.
4. **Security agent is read-only.** An agent that can detect AND fix problems is an agent that can cause problems.
5. **Monitor before you scale.** Add observability before adding complexity.

## Getting Started

1. Start with one agent, one channel, one model
2. Add a second agent with a different specialty + routing
3. Add monitoring and alerting
4. Add provider failover + credit limits

## License

MIT
