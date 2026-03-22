---
layout: default
title: AI Agent Swarm
---

# I Built a Self-Healing AI Agent Swarm That Runs My Infrastructure

Everyone's excited about connecting Claude to a notes app. I went a different direction.

I built a multi-agent system with 5 specialized AI agents, 3 cloud providers, automatic failover, credit-based routing, and self-healing monitoring. It handles everything from "what's for dinner" to "debug this production issue" -- and it decides which AI model to use for each.

Here's the full architecture.

---

## The Problem With "One Agent to Rule Them All"

The Claude + Obsidian approach works. You get persistent memory, some tool access, and a chatbot that remembers your preferences. That's genuinely useful.

But I kept hitting the same wall: the wrong model was answering the wrong questions.

Asking a frontier model "what's the weather?" is like hiring a surgeon to put on a band-aid. Asking a cheap model to architect a distributed system is like asking the band-aid to do surgery.

I needed routing.

---

## The Swarm

The platform runs on my local machine and a VPS, connected bidirectionally. Here's who lives in the swarm:

### Hub (The Dispatcher)
Every message I send -- across multiple chat channels -- hits the Hub first. Hub classifies the message into one of 9 categories and routes it to the right agent on the right model.

Hub itself runs on free/cheap models for trivial stuff. It never touches an expensive model unless it has to.

### Main Agent (The Daily Driver)
My primary agent for complex reasoning. Runs on the best reasoning model available, with fallbacks to two other providers. This is who I'm talking to when I need actual thinking.

### Code Agent (The Specialist)
Pure code tasks. Runs the best code-specialized model available. Minimal tool access, restricted filesystem scope. It can't break things it can't reach.

### Security Agent (The Watchdog)
Runs over a dozen automated security checks on a regular schedule:
- File permission audits
- Secrets-in-git detection
- Open port scanning
- Process anomaly detection
- Login monitoring
- Disk and log usage tracking

Critically: the Security Agent is **read-only**. It detects and reports. It never modifies files. If it finds something critical, it alerts me immediately. Lower-priority warnings get batched.

### Personal Agent
My partner has their own agent on a separate channel. Completely independent from the swarm -- own personality, own workspace, own context.

---

## The Routing Table

This is the core insight: match the task to the cheapest model that can handle it.

| Category | Model Tier | Why |
|----------|-----------|-----|
| Trivial ("hi", "thanks") | Free tier | Why pay for pleasantries? |
| Simple (quick questions) | Fast mid-tier | Good enough, cheap |
| Lookups (facts, definitions) | Fast mid-tier | Retrieval, not reasoning |
| Data (analysis, summaries) | Fast mid-tier | Structured output, bulk work |
| Ops (infra management) | Strong mid-tier | Needs deeper context |
| Code | Code-specialized | Purpose-built |
| Security | Strong mid-tier | Pattern matching at scale |
| Complex (multi-step reasoning) | Top reasoning | Best reasoning available |
| Hardest (architecture, strategy) | Maximum capability | When nothing else will do |

Every fallback chain spans all 3 major AI providers. No single point of failure.

---

## The Credit Economy

Each agent gets a daily credit budget, refilled automatically. This isn't a billing system -- it's a **circuit breaker**.

If a rogue loop starts hammering the API, it burns through credits and stops. Hub falls back to the free tier and alerts me instantly.

A guard script validates every state change. It blocks dangerous operations like task deletions, agent removals, and routing wipes. Every write gets auto-backed up before it happens.

I've never had a runaway cost incident. The circuit breaker makes sure I never will.

---

## The Infrastructure

### Local Machine (Primary)
- Gateway + all agents
- Development CLI integration
- Backup agent framework

### VPS (Always-On)
- Second gateway
- Database + cache
- Workflow automation engine
- Monitoring dashboard
- Reverse proxy (all services behind HTTPS)
- Local LLM for offline/private tasks

Both machines run a gateway AND connect to the other as a node. Either can delegate work to the other. Local handles the heavy AI work; the VPS handles monitoring, workflows, and always-on services.

### Monitoring Stack
- Health checks every few minutes, auto-discovering services
- Multiple monitoring probes with instant chat alerts
- Workflow automations for usage tracking and cost threshold alerts
- Daily backups with auto-pruning retention

---

## Security

This isn't a toy. Real infrastructure needs real security.

I won't go into specifics (for obvious reasons), but the posture includes:

- Key-only authentication with intrusion detection
- Firewall with strict policies
- All services behind a reverse proxy -- zero directly exposed ports
- API keys stored securely with automated rotation on a schedule
- Bot access restricted to allowlists
- A dedicated read-only security agent running continuous automated scans
- Per-agent tool restrictions and execution policies

The security agent being read-only was the single best architectural decision in this project. An agent that can both detect problems AND fix them is an agent that can cause problems.

---

## What It Actually Costs

| Item | Monthly Cost |
|------|-------------|
| VPS | ~$12 |
| API usage | Variable |
| Free-tier model | $0 |
| Search API | ~$25 |
| **Infrastructure total** | **~$37 + API** |

The routing optimization is the cost control. Most messages (trivial, lookups, simple questions) hit free or near-free models. Only genuinely complex tasks touch expensive ones.

---

## What I'd Build Differently

1. **Start with monitoring, not agents.** I added monitoring after complexity and had a few blind spots early on. Monitor first, then add agents.

2. **One agent, one job.** Separation of concerns applies to AI agents just like it does to microservices. The security agent being read-only proves this.

3. **Circuit breakers from day one.** Even if you trust your code, add them. The one time you need them, you'll be very glad they exist.

4. **Provider diversity isn't optional.** Every major AI API provider has had outages recently. If your system depends on one provider, your system has a single point of failure.

---

## Getting Started

If you want to build something like this, here's the progression:

1. **Week 1**: One agent, one channel, one model. Get the basics working.
2. **Week 2**: Add a second agent with a different specialty. Add routing between them.
3. **Week 3**: Add monitoring and alerting. You should know when things break before you notice.
4. **Week 4**: Add provider failover and credit limits. Now you're production-ready.

The "Claude + Obsidian" approach is step 0.5. It's a great place to start. But if you want AI that actually operates -- not just assists -- you need the full stack.

---

*Happy to share more about the architecture. Reach out if you're building something similar.*

[View on GitHub](https://github.com/mbsebada/ai-agent-swarm)
