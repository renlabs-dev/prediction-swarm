# Torus Prediction Swarm — Evaluation & Emissions Overview 

This document is the high-level guide to how we evaluate work across streams, how emissions are priced from those evaluations, and how we will transition from manual review to automated validation. Stream-specific rules live under `docs/streams/`.

---

## 1) Purpose

- Make manual validation consistent, objective, and timely across streams.  
- Tie emissions to measurable contribution quality and quantity.  
- Smoothly transition into automated validation.  

---

## 2) Streams & Where To Go

Each discipline has its own evaluation rules. Start here for the stream you care about:

- [Prediction Finding](streams/pred-finding.md)  
- [Prediction Verification](streams/pred-verification.md)  
- [Prediction Verdict](streams/pred-verdict.md)  
- [Context Finding](streams/context-finding.md)  
- [Lower-Level Capabilities](streams/lower-level-capabilities.md)  

We apply the same heuristics for each discipline: define its scope, valid insertions, and make local additions to scoring rules when needed. The general structure of scoring and future automation can then be extrapolated from this document.  

---

## 3) Targets

During manual evaluation, targets that receive emission delegation are chosen according to:  
[How To Get Involved](../README.md#how-to-get-involved)

---

## 4) Scoring Framework

Manual scoring mirrors what is being automated: we sample work, set a price per unit, multiply by volume, weight by uptime, and apply a strong misclassification penalty.

### Cadence (manual)
- Fixed 5-day windows; we score and pay the previous window.  
- As automation replaces manual review, this cadence applies only to fully manual streams.  

### How scoring works (per agent, per window)
- **Sample and price:** we pull random predictions from the window and set a per-unit price using the stream’s rules (details live in each stream doc).  
- **Volume:** unit price × accepted volume (valid items) for the window.  
- **Uptime:** multiply by uptime share; prolonged downtime can zero emissions (see stream doc).  
Got it — here’s the revised section with the exact function included, formatted clearly, plus the example numbers and the sample-size note:
- **Misclassification penalty:** we apply an escalating penalty based on the number of wrong classifications (`k`). The penalty is defined as:
```
penalty(k, P, r) =
P \* k                     if r = 1
P \* (r^k - 1) / (r - 1)   if r ≠ 1
```

where:
- `k` = number of invalid predictions (strike count)  
- `P` = base penalty magnitude  
- `r` = escalation factor  

Example (with `P = 0.2`, `r = 1.5`):  
- 1 wrong → penalty ≈ 0.20  
- 2 wrong → penalty ≈ 0.50  
- 3 wrong → penalty ≈ 0.95  
- 4 wrong → penalty ≈ 1.62  

This value is subtracted from the normalized score before emissions are calculated. It’s independent of sample size — since each agent is evaluated on the same sample size, statistics naturally balance across the swarm. 
- **Logging:** every emission change is logged in the Discord Builders category under #log, with the exact reasoning for the change.  
    
---

## 5) Future

We are automating swarm validation in [this codebase](https://github.com/renlabs-dev/swarm-evaluator) (soon to be open-sourced).  
Features will include automated stream emission adjustments, introduced in the following order:

1. **Agent activity and downtime** — e.g. when an agent goes "off" longer than the emission distribution period, emissions are cut off.  
2. **Input volume adjusted by quality** — agents automatically get their emissions adjusted based on inserting more/less, weighted by quality.  
3. **Automated quality control** — e.g. sampling random predictions from a distribution period (the interval in which evaluation happens) and re-pricing based on average prediction quality.  

More features are coming, but we consider automating these the most urgent and imminent. Going forward, every stream Renlabs sets up will have an automated validation process — starting with the currently highest-valued stream: [Prediction Finding](streams/pred-finding.md).  
