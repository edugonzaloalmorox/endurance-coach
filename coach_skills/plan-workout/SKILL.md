---
name: plan-workout
description: Plans one safe cycling workout from recent training activities and current fatigue. Use when a cyclist asks what ride to do next or requests a workout recommendation.
metadata:
  author: endurance-coach
  version: "0.1.0"
---

# Plan a cycling workout

Create one workout for the requested date. Base the decision only on the supplied activities and
training summary; do not invent health, recovery, or power data.

## Process

1. Check that at least one recent activity is available. If not, ask for training data instead of
   prescribing a workout.
2. Review the recent duration, power-based training stress, missing-data counts, and any explicitly
   known hard/easy sequence. Do not infer intensity or perceived exertion when those fields are
   null.
3. Prefer recovery or endurance after a demanding interval or long-ride day. Do not prescribe two
   high-intensity days in succession.
4. Return exactly one recommendation matching the `WorkoutRecommendation` contract.
5. Make all step durations add up to the workout's total duration.

## Exact output shape

Return one JSON object with exactly these fields and nested field names:

```json
{
  "workout_date": "YYYY-MM-DD",
  "title": "short title",
  "ride_kind": "recovery | endurance | tempo | intervals | long_ride",
  "duration_minutes": 60,
  "objective": "intended training outcome",
  "rationale": "explanation tied to supplied evidence",
  "evidence": [
    {
      "observation": "factual observation from the supplied context",
      "source": "deterministic_training_summary or recent_activities"
    }
  ],
  "uncertainty": {
    "level": "low | medium | high",
    "reasons": ["required when level is medium or high"]
  },
  "warnings": ["missing-data or safety limitation"],
  "steps": [
    {
      "name": "segment name",
      "duration_minutes": 60,
      "intensity": "actionable RPE or conversational cue"
    }
  ],
  "source_skill": "plan-workout"
}
```

Do not rename nested fields or add measurement fields inside `evidence` or `uncertainty`. Every
evidence item must contain both `observation` and `source`. Use only facts already present in the
supplied context, and keep the sum of all step durations equal to `duration_minutes`.

## Intensity language

- Recovery: conversational, RPE 1-2.
- Endurance: steady aerobic riding, RPE 3-4.
- Tempo: controlled pressure, RPE 6-7.
- Intervals: repeatable hard work, RPE 8; include recovery between efforts.

## Safety and missing data

When power is unavailable, use RPE language and add a warning. Never diagnose illness or injury.
If the athlete reports pain, illness, or unusual exhaustion, recommend rest and appropriate
professional advice rather than a training session.

