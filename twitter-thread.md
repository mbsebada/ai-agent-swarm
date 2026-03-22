# X Thread Draft

> Hook into the "Claude + Obsidian" conversation. Show what happens when you go way deeper.

---

**1/**
Everyone's talking about giving AI a brain with Obsidian.

I gave AI a nervous system, and now it runs my entire infrastructure.

It took 2 weeks to build. Here's how it works:

---

**2/**
The setup everyone shares: Claude + notes app + a few MCP connectors.

My setup: 5 specialized AI agents, 3 cloud providers, a VPS, automatic failover, credit-based routing, and self-healing monitoring.

Same idea. Very different scale.

---

**3/**
Meet the swarm:

- **Hub** -- dispatcher. Classifies every message into 9 categories and routes to the right agent + model
- **Main** -- my daily driver. Complex reasoning
- **Code** -- code specialist
- **Security** -- watchdog. Automated scans, read-only, never modifies files
- **Personal** -- a separate agent for my partner (outside the swarm)

---

**4/**
The routing is the magic.

"What's the weather?" -> free model (instant)
"Summarize this doc" -> fast mid-tier model
"Review this PR" -> code-specialized model
"Debug this production issue" -> top reasoning model
"Architect this system" -> maximum capability model

Every message gets the cheapest model that can handle it. No waste.

---

**5/**
Each agent has a daily credit budget. This isn't for billing -- it's a circuit breaker.

If something goes haywire and starts spamming API calls, it hits the credit wall and stops. The hub falls back to a free model and alerts me.

No runaway costs. Ever.

---

**6/**
Every routing chain covers all 3 providers:

Code: Provider A -> Provider B -> Provider C
Security: Provider B -> Provider A -> Provider C
Complex: Provider C -> Provider B -> Provider A

If any provider goes down, the next one picks up automatically. Zero downtime.

---

**7/**
The infrastructure runs itself:

- Health checks every few minutes (auto-discovers active services)
- Multiple monitoring probes with instant alerts
- Workflow automations for usage tracking and cost alerts
- Daily backups with auto-pruning
- Automated API key rotation

---

**8/**
Security is baked in, not bolted on:

- Key-only auth, intrusion detection, firewall
- All services behind a reverse proxy (no exposed ports)
- Dedicated security agent runs automated scans on a loop
- Strict file permissions across the board
- Bot access locked to allowlists

---

**9/**
My local machine and VPS talk to each other bidirectionally.

Local runs the agents. VPS runs monitoring + workflows.
Both can delegate work to each other.

I message my phone -> Hub classifies -> routes to the right agent -> right model -> right machine.

---

**10/**
Total cost to run this:

- VPS: ~$12/mo
- API spend: varies, but routing optimization keeps it way down
- My time: 2 weeks to build, <1 hr/week to maintain

"It costs almost nothing to run" isn't marketing. It's architecture.

---

**11/**
What I'd tell you if you're starting:

1. Start with one agent that does one thing well
2. Add routing when you hit the "wrong model for the task" problem
3. Add monitoring before you add complexity
4. Provider failover isn't optional -- APIs go down
5. Credit limits save you from yourself

---

**12/**
The "Claude + Obsidian" approach is a great starting point. Seriously.

But if you want AI that actually runs your operations -- not just answers questions -- you need agents that specialize, route intelligently, fail gracefully, and monitor themselves.

That's what a swarm does.

---

**13/**
Building this in public. Happy to share the architecture if you're interested.

Drop a reply or DM if you want details.

[end thread]
