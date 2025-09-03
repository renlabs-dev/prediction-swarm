# Stream: Prediction Finding — Evaluation & Scoring

## 1) Scope & Goal

- Find and capture predictions made by identifiable authors with sufficient evidence to verify later.
- Prioritize high‑value **crypto related** predictions, with clear verification paths.

---

## 2) What Counts As A Prediction

A prediction is a forward looking claim that could resolve true or false within finite time
Crypto prediction means the claim is about crypto assets markets protocols or usage metrics
Ecosystem label reflects the primary chain or ecosystem referenced. If the post is about BTC or broad markets with no specific chain focus set ecosystem to other
---

## 3) Valid Prediction Checklist

A submitted item is valid if it passes all checks:
1. **Consequential**: Non-trivial, domain-relevant, and not purely local/personal.  
2. **Attributable & timestamped**: Clear author and verifiable publication time.  
3. **Well-defined**: Outcome is measurable with explicit resolution source, units, and tie-breaks.  
4. **Evaluable**: Structured so it can be scored (format + proper scoring rule).  
5. **Resolvable**: Clear path to adjudication, including conditions or revisions.  

---

## 4) Prediction Types

**By outcome space**
- **Binary**: Yes/no event (e.g., “Will X happen by date D?”).
- **Multiclass categorical**: One of several discrete outcomes (e.g., “Which chain lists first?”).
- **Ordinal categorical**: Ordered buckets (e.g., “Top-1/2/3 outcome”).
- **Continuous scalar**: Real-valued metric at time D (e.g., price, TVL).
- **Count / rate**: Non-negative integer or rate over a window (e.g., incidents in Q4).
- **Time-to-event**: Distribution over when an event occurs (e.g., “When will upgrade launch?”).
- **Comparative / precedence**: Relative ordering (e.g., “Will A occur before B?”).
- **Joint / conditional**: Probability of combined or conditional events (e.g., “If X, then chance of Y by D”).
- **Trajectory / vector**: Sequence of values over time (e.g., monthly users for 6 months).
- **Ranking / top-k**: Predicted order or selection among items.

**By elicitation format**
- **Point**: Single best guess.
- **Interval**: Lower/upper bound with confidence level.
- **Quantiles**: Specific quantile forecasts (e.g., 10/50/90).
- **Full distribution**: Complete probability distribution over outcomes.


---

## 5) Scoring 

Total score ranges from 0 to 100, the influencing factors sorted by relevance are:

- **Consequentiality** — Should make up most of the prediction quality.  
  If a prediction is not consequential, quality goes instantly to 0.  

- **Verifiability** — Prediction should ideally be easily verifiable.  
  If it is consequential but hard to evaluate, quality goes down.  

- **Clarity & Specificity** — Predictions should use precise metrics, explicit timelines, and clear conditions.  
  Ambiguous or vague claims lower quality.  
  
---

**Bonuses**
- **Submit Older Predictions** — We can make immediate validation, hence such predictions are more valuable for us.  
