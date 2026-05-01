# Demo Talk Track: Network Infrastructure Monitoring with Grafana Cloud

**Audience:** Network engineers and admins at a large enterprise bank with limited observability tooling.
**Duration:** 20–30 minutes
**Dashboard:** Network Infrastructure Overview

---

## Opening (2 min)

> "Today I want to show you what full-stack network observability looks like. Most network teams I talk to are running with SNMP polling on 5-minute intervals, maybe some syslog forwarding to a box nobody checks, and a lot of tribal knowledge about which devices are 'the flaky ones.' Sound familiar?
>
> What I'm going to walk through is a live environment modeled after your topology — dual-site, active-active data centers, core routers with BGP upstream, F5 load balancers fronting your application tiers, and Cisco switching infrastructure. Everything you see here is generating real telemetry right now."

## The Single Pane of Glass (3 min)

Start at the top of the dashboard.

> "First thing — one screen, everything that matters. Your KPIs across the top: devices online, BGP sessions, average CPU, active load balancer connections, pool member health, and request rate. These update every 15 seconds.
>
> Below that, the network topology canvas. Every icon represents a real device. The connection lines are animated — you can see the data flow. Green means healthy. If something goes orange or red, you'll see it here before a user calls.
>
> Next to the topology, the Device Health table gives you CPU, memory, and temperature for every device at a glance. And the Pool Member Health table shows the status of every backend server behind your F5s."

**Click on the site dropdown** and filter to `dc-east`, then `dc-west`, then back to `All`.

> "Everything is filterable by site. When you're troubleshooting at 2 AM, you want to narrow scope fast."

## Discovering the Problem (5 min)

Scroll down to the Device Health section.

> "Now let me show you what makes this powerful. Look at the temperature gauges. Six of our seven devices are sitting comfortably in the green — low 30s. But lb-01 in dc-east? That's running in the mid-40s, sometimes spiking above 50. That's our problem child.
>
> Now look at the CPU chart. See that one line running way above the others? That's lb-01 again. When the temperature spikes, the CPU follows — thermal throttling kicks in, the device works harder to maintain the same throughput, which generates more heat. It's a feedback loop.
>
> With your current tooling, you'd know something is wrong when pool members start failing health checks and application teams start filing tickets. But by then you're already in an incident. Here, the temperature trend told us about this problem days ago."

## Correlating Metrics and Logs (5 min)

Scroll to the Load Balancer section.

> "Let's dig deeper into what lb-01's thermal issue is actually causing. Look at the HTTP request rate panel — see the 5xx error rates. lb-01 is throwing significantly more 502s and 503s than lb-02. If you were only looking at aggregate error rates, you'd see 'errors are up' but not *why*.
>
> The request latency histograms tell the same story — lb-01's p95 latency is noticeably higher."

Now scroll to the Network Event Logs panel at the bottom.

> "Here's where metrics and logs come together. These aren't just syslog messages dumped into a text file — they're structured, searchable, and correlated with the metrics above.
>
> Watch for the thermal warnings on lb-01 — 'CPU temperature exceeded 50C.' Fan speed ramping up. SSL handshake timeouts. Pool members flapping DOWN and RESTORED. You can see the *story* — the device overheats, performance degrades, pool members fail health checks, traffic shifts to the remaining members, lb-01 cools down slightly, members come back, and the cycle repeats.
>
> With separate syslog and SNMP tools, you'd be correlating timestamps in your head across two different screens. Here it's one scroll."

## The BGP Story (3 min)

Scroll to the BGP & Routing section.

> "While we're here — see the BGP session table. We have an intermittent flap on core-rtr-01's session to AS65200. The session drops, prefixes go to zero, then it re-establishes. Each flap means a routing reconvergence — your traffic takes a different path for a few seconds.
>
> In the routing table entries panel, you can see the BGP route count dip when that session drops. If this happens during peak hours, your users feel it as a brief latency spike.
>
> The question for your team is: how long has this been happening? With Grafana Cloud, you can zoom out to a week, a month, and see the pattern. Was it always this peer? Did it start after a config change? That's the difference between 'we know it flaps sometimes' and 'it started flapping on March 15th, which is when the upstream changed their route policy.'"

## The 'What If' Moment (3 min)

> "Now let me ask you this: if lb-01 failed completely right now — hard down — what happens?
>
> You can answer that question from this dashboard. Look at the pool member table: lb-02 in dc-west has all its members healthy. The BGP sessions on core-rtr-02 are stable. Traffic would shift west, lb-02 would absorb the load. Your connection table utilization on lb-02 is well below capacity.
>
> You can make that call in 10 seconds from this dashboard. Without it, that's a 30-minute war room conversation before anyone is confident enough to say 'yes, we can survive losing dc-east.'"

## Alerting (2 min)

> "Everything we've looked at can drive alerts. Temperature over 45 for 5 minutes? Alert. More than 2 pool members down on the same LB? Alert. BGP session flapping more than 3 times in an hour? Alert.
>
> The difference is these alerts have *context*. When your on-call gets paged for lb-01 temperature, they click the link, land on this dashboard, and immediately see the CPU correlation, the pool member impact, and the log events. They don't have to SSH into the box, run `show tech`, grep through syslog, and piece the story together manually."

## Closing (2 min)

> "What I've shown you today is:
>
> 1. **Unified visibility** — metrics, logs, and device topology in one place
> 2. **Proactive detection** — the temperature trend on lb-01 is visible long before it causes an outage
> 3. **Fast correlation** — when something breaks, you see the full cause-and-effect chain immediately
> 4. **Capacity planning** — you can answer 'can we survive losing a site' at any moment
>
> This runs on Grafana Cloud — no infrastructure to manage, no collectors to patch, no database tuning. Your Alloy agent collects everything and ships it. You focus on the network, not the monitoring system.
>
> The demo environment you're looking at took about an hour to set up. Your real environment has more devices, but the pattern is the same: deploy Alloy, point it at your SNMP targets, and start building dashboards. We can have you seeing real data from your network within a day."

---

## Key Talking Points to Emphasize

| Their Pain | Our Answer |
|---|---|
| "We only know about problems when users complain" | Temperature trend on lb-01 was visible before any user impact |
| "Our SNMP tool polls every 5 minutes" | 15-second scrape interval, sub-minute visibility |
| "Logs are on a separate system nobody checks" | Metrics and logs in one dashboard, correlated by device |
| "We can't tell if we'd survive a site failure" | Capacity data is always visible, no guessing |
| "Alert fatigue — too many meaningless alerts" | Threshold-based alerts with dashboard context links |
| "We need 3 tools open to troubleshoot" | One dashboard, one scroll, full picture |

## Demo Gotchas

- **lb-01 is intentionally degraded** — it will show elevated temperature, CPU, error rates, and pool member flaps. This is the story.
- **BGP flap on core-rtr-01 ↔ AS65200** is intermittent — if it hasn't happened recently, mention "it's an intermittent issue, let me show you the log entries from the last occurrence."
- **If logs panel is empty**, check the time range — Loki queries default to the dashboard time picker. Widen to 1h or 3h.
- **Pool member flaps** are probabilistic — during the demo, you may see 1–3 DOWN events on lb-01. If none have fired yet, scroll the logs panel to find a recent one.
