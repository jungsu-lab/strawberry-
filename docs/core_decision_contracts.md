# BerryNext Core Decision Contracts

These contracts define stable dataclasses for the final decision-support pipeline.
They do not implement GAM, agronomic threshold values, or actuator commands.

```text
Sensor Data
-> Current State Builder
-> Environmental Predictor
-> Scenario Simulator
-> Threshold / Literature Rule Engine
-> Work-Need Scorer
-> Recommendation Generator
```

## Dataclasses

| Pipeline stage | Contract | Purpose |
| --- | --- | --- |
| Current State Builder | `CurrentGreenhouseState` | Normalized current greenhouse state with sensor-quality metadata. |
| Environmental Predictor | `EnvironmentalPrediction` / extended `PredictionResult` | Short-term environmental delta output, including model/fallback metadata. |
| Scenario Simulator | `ScenarioCandidate` | Candidate action or no-action branch for what-if comparison. |
| Work-Need Scorer | `WorkNeedScore` | 0-100 work-need score with stress/risk components and confidence. |
| Recommendation Generator | `CoreRecommendation` / extended `RecommendationResult` | Human-reviewed decision-support recommendation output. |

## Boundaries

- `EnvironmentalPrediction` may be produced by a baseline or a future GAM, but the contract is model-independent.
- `ScenarioCandidate` represents decision-support comparisons only. It is not an actuator command.
- `WorkNeedScore` validates numeric ranges but does not contain hard-coded cultivation thresholds.
- `CoreRecommendation.mode` is always `decision_support`.
- Recommendations require human review and should remain separate from actuator examples.
