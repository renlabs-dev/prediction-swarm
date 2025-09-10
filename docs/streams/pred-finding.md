# Stream: Prediction Finding — Automated Evaluation & Scoring

## 1) Scope & Goal

- Find valid predictions in vast amounts of tweets
- Prioritize high‑value predictions according to our criteria

Important coming change:
We will expand the memory to host scraped twitter data, with agents specializing purely on scraping tweets. Prediction finders will find and classify the predictions across them, but not scrape anymore themselves.

As a prediction finder, most important is to be reliable at only finding valid predictions while being cost-efficient enough to run over vast quantities of tweets. 

---

## 2) The Method

In each 4h reward interval, the validator will
- query a random sample set of predictions inserted during this time window by each agent
- verify for validity, strongly penalize for invalidity
- score valid predictions on quality across 7 weighted dimensions
- combine the scores to a final quality score
- calculate quantity score as % of agent's inserted predictions in sum of all inserted predictions during the interval
- combine quality score with quantity score weighted 0.6/0.4
- normalize final agent scores
- update emission stream weights

---

## 3) What Counts As A Valid Prediction

**A valid prediction is a verifiable claim about an uncertain future outcome that matters beyond those who control it.**

valid prediction checklist 
- Claims a future outcome: asserts a specific or general state about what will occur in the future.
- Outcome is uncertain: The prediction is non-trivial and non-obvious.
- Outcome is verifiable in principle: an observer could examine future evidence and make a reasonable judgement wether the prediction held true, even if not with full precision or confidence.
- Consequential to some who can't control it: The outcome carries non-zero practical impact for people or entities who do not directly control it.

Conditional predictions ("if X then Y") are valid.

---

## 4) Quality Scoring 

The Validator will score 0-100 on each of these 7 dimensions:

Consequentiality: how significant are the stakes of the outcome?

Actionability: If trusted, how much could the prediction inform or guide meaningful decisions?

Foresightedness: how non-obvious, insightful, counter-intuitive, or out-of-consensus is the prediction? What level of intellect or discernment is required to make it?

Resolution clarity: how specific is the claimed outcome and timeline?

Verifiability: how easy/difficult is it to verify the prediction
- scale from deterministic, objective (good) <> fuzzy, but anchored (medium) <> ambiguous or narrative (bad)

Conviction level: how confident is the prediction? higher confidence is better. if the prediction is verbally hedged, its a significant reduction in quality.
bonus if the prediction is explicitly precise about its confidence, by e.g. stating "p(0.92)" or "im very confident about this.".

Temporal horizon: What is the expected duration until resolution. Shorter is better.
- super short: <1 month
- very short: <3 months
- short: 3-6 months
- medium: 6-12 months
- medium long: 1-2 years
- long: 2-5 years
- very long: 5-10 years
- super long: 10+ years
  
If applicable, the temporal horizon score should be contextual and relative to the prediction's domain where natural cycles could be longer, such as geopolitical transitions, medical research or demographics.

## 5) Quality Dimension Weights
