---
name: analyze-training
description: Analyzes recent cycling training from supplied deterministic metrics and dated activities. Use when a cyclist asks about training patterns, load, consistency, progress, or what the evidence suggests.
metadata:
  author: endurance-coach
  version: "0.1.0"
---

# Analyze recent cycling training

Turn the supplied deterministic metrics and dated activities into an evidence-based training
analysis. Keep observed facts, interpretations, and unavailable evidence distinct. End with one
cautious next-workout recommendation matching the required `WorkoutRecommendation` contract.

## Process

1. Identify the athlete's question and select only the evidence needed to answer it. Use the
   supplied `deterministic_training_summary` for aggregates, its `training_load` report for load
   measures and coverage, and `recent_activities` for dated session facts.
2. If the runtime advertises deterministic metric tools, call only the minimum relevant tools and
   use their returned values. Never calculate totals, trends, training stress, intensity, or other
   metrics in the model. Do not call or invent a tool that the runtime has not advertised.
3. Build the analysis in three parts before recommending a workout:
   - **Observed:** exact facts from the supplied summary, activities, or tool results, retaining
     dates, units, sample scope, and source.
   - **Interpreted:** cautious explanations supported by those observations. Label associations as
     interpretations; do not present them as measured facts or causal conclusions.
   - **Unavailable:** evidence required by the question that is missing, null, outside the supplied
     period, or unsupported by a deterministic tool.
4. Use the observed facts in `evidence`, put interpretations in `rationale`, and put unavailable or
   conflicting evidence in `uncertainty` and `warnings`.
5. Return exactly one recommendation matching the runtime-provided `WorkoutRecommendation` schema.
   Set `source_skill` to `analyze-training`, and make all step durations add up to
   `duration_minutes`.

## Evidence and provenance

- Every numerical claim must reproduce a supplied deterministic value; retain its unit and dated
  window or activity date.
- Treat a partial load value as the sum of its usable samples, not as the complete load for the
  period. Repeat its sample size, missing-activity count, and limitation when citing it.
- Every evidence item must name its actual source, such as `deterministic_training_summary`,
  `recent_activities`, or a named deterministic tool result.
- Do not convert missing values into zero. A total over available values does not prove that the
  missing activities contributed zero.
- Do not infer power, heart rate, intensity, recovery, sleep, soreness, readiness, or perceived
  exertion from duration, distance, title, or ride type.
- Do not claim a trend, improvement, decline, or fatigue effect unless the supplied evidence
  includes comparable periods or observations sufficient for that comparison.

## Uncertainty and safety

Use higher uncertainty when important measurements are missing, the sample is small, dates are
stale, sources conflict, or the requested comparison is unavailable. State the specific limitation
instead of filling the gap with general cycling assumptions.

Never diagnose illness, injury, or overtraining. If the athlete reports pain, illness, or unusual
exhaustion, recommend rest and appropriate professional advice. Do not apply or imply an automatic
change to a training plan; the athlete must approve any proposed change.
