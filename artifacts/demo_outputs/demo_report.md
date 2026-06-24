# Strawberry Decision-Support Demo Report

Rule-based assumptions and literature/manual evidence are used unless a model passes confidence gates.
Scenario outputs are decision support, not validated causal simulation or control commands.

## Irrigation check: high VPD with low substrate moisture

- Expected focus: `irrigation`
- Focus recommendation: `irrigation` high confidence=0.25: substrate moisture is below the literature starting threshold, VPD is high, indicating higher transpiration demand, radiation is high enough to raise water-demand attention
  - Risks: confirm recent irrigation, drainage, and sensor units before changing volume; usable training rows are below the configured minimum
  - Safety: decision_support_only, requires_human_review, insufficient_training_rows, insufficient_data_fallback, rule_based_fallback
- Full ranking highlights:
  - `shading_high_temperature` high confidence=0.8: temperature is in a high-temperature caution range, radiation is high, VPD is high
    - Risks: excess shading can reduce photosynthesis and delay ripening
    - Safety: decision_support_only, requires_human_review
  - `irrigation` high confidence=0.25: substrate moisture is below the literature starting threshold, VPD is high, indicating higher transpiration demand, radiation is high enough to raise water-demand attention
    - Risks: confirm recent irrigation, drainage, and sensor units before changing volume; usable training rows are below the configured minimum
    - Safety: decision_support_only, requires_human_review, insufficient_training_rows, insufficient_data_fallback, rule_based_fallback
  - `harvest_monitoring` low confidence=0.38: visible fruit count supports harvest review, high temperature can increase quality-loss risk
    - Risks: market target and distribution temperature can change harvest thresholds
    - Safety: decision_support_only, requires_human_review
- What-if directions:
  - `irrigation`: moisture likely increases
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required; model prediction fallback: usable training rows are below the configured minimum
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `shading_high_temperature`: heat stress may decrease; water demand may decrease
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `nutrient_ec_check`: EC issue becomes better characterized; EC issue remains unresolved until fertigation is adjusted
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `no_action`: current trend likely continues; EC issue remains unresolved
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.

## Ventilation/dehumidification: high humidity with low VPD

- Expected focus: `ventilation_dehumidification`
- Focus recommendation: `ventilation_dehumidification` high confidence=0.76: humidity is high, low VPD suggests wet-canopy conditions
  - Risks: human review is required before ventilation or dehumidification control changes
  - Safety: decision_support_only, requires_human_review
- Full ranking highlights:
  - `disease_environment_risk_proxy` high confidence=0.82: environmental disease risk proxy review, humidity is high, VPD is low, rain probability increases monitoring attention
    - Risks: not actual disease prediction without disease labels
    - Safety: decision_support_only, requires_human_review, requires_field_confirmation
  - `ventilation_dehumidification` high confidence=0.76: humidity is high, low VPD suggests wet-canopy conditions
    - Risks: human review is required before ventilation or dehumidification control changes
    - Safety: decision_support_only, requires_human_review
  - `leaf_removal_caution` medium confidence=0.54: cautious leaf removal review only, leaf density is high, humidity suggests airflow review
    - Risks: avoid aggressive or repeated leaf removal that reduces plant vigor
    - Safety: decision_support_only, requires_human_review
- What-if directions:
  - `ventilation_dehumidification`: humidity may decrease; disease environmental risk may decrease
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `heating_low_temperature`: temperature likely increases; low-temperature stress may decrease
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `no_action`: current trend likely continues; EC issue remains unresolved; disease environmental risk may remain elevated
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.

## Nutrient/EC check: high root-zone and drainage EC

- Expected focus: `nutrient_ec_check`
- Focus recommendation: `nutrient_ec_check` high confidence=0.82: root-zone or drainage EC is high, feed EC is above the starting Seolhyang range, compare root-zone EC with drainage EC before changing fertigation
  - Risks: do not diagnose plant nutrient status from EC alone
  - Safety: decision_support_only, requires_human_review
- Full ranking highlights:
  - `nutrient_ec_check` high confidence=0.82: root-zone or drainage EC is high, feed EC is above the starting Seolhyang range, compare root-zone EC with drainage EC before changing fertigation
    - Risks: do not diagnose plant nutrient status from EC alone
    - Safety: decision_support_only, requires_human_review
  - `irrigation` low confidence=0.36: substrate moisture is below the literature starting threshold
    - Risks: confirm recent irrigation, drainage, and sensor units before changing volume; recent irrigation history should reduce urgency until response is checked
    - Safety: decision_support_only, requires_human_review
  - `harvest_monitoring` low confidence=0.28: visible fruit count supports harvest review
    - Risks: market target and distribution temperature can change harvest thresholds
    - Safety: decision_support_only, requires_human_review
- What-if directions:
  - `nutrient_ec_check`: EC issue becomes better characterized; EC issue remains unresolved until fertigation is adjusted
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `irrigation`: moisture likely increases; EC issue may dilute only if drainage is adequate
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `no_action`: current trend likely continues; EC issue remains unresolved
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.

## Heating/thermal protection: low night temperature

- Expected focus: `heating_low_temperature`
- Focus recommendation: `heating_low_temperature` high confidence=0.25: low temperature may slow strawberry growth, low temperature is near a stronger thermal protection trigger, outside temperature raises heat-retention attention
  - Risks: consider energy cost and humidity rise when vents are closed; usable training rows are below the configured minimum
  - Safety: decision_support_only, requires_human_review, insufficient_training_rows, insufficient_data_fallback, rule_based_fallback
- Full ranking highlights:
  - `heating_low_temperature` high confidence=0.25: low temperature may slow strawberry growth, low temperature is near a stronger thermal protection trigger, outside temperature raises heat-retention attention
    - Risks: consider energy cost and humidity rise when vents are closed; usable training rows are below the configured minimum
    - Safety: decision_support_only, requires_human_review, insufficient_training_rows, insufficient_data_fallback, rule_based_fallback
  - `ventilation_dehumidification` medium confidence=0.25: low VPD suggests wet-canopy conditions
    - Risks: human review is required before ventilation or dehumidification control changes; usable training rows are below the configured minimum
    - Safety: decision_support_only, requires_human_review, insufficient_training_rows, insufficient_data_fallback, rule_based_fallback
  - `disease_environment_risk_proxy` low confidence=0.38: environmental disease risk proxy review, VPD is low
    - Risks: not actual disease prediction without disease labels
    - Safety: decision_support_only, requires_human_review, requires_field_confirmation
- What-if directions:
  - `heating_low_temperature`: temperature likely increases; low-temperature stress may decrease
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required; model prediction fallback: usable training rows are below the configured minimum
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `ventilation_dehumidification`: humidity may decrease; disease environmental risk may decrease
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required; model prediction fallback: usable training rows are below the configured minimum
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `no_action`: current trend likely continues; EC issue remains unresolved
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.

## Leaf removal caution: dense canopy with recent leaf work

- Expected focus: `leaf_removal_caution`
- Focus recommendation: `leaf_removal_caution` low confidence=0.34: cautious leaf removal review only, leaf density is high, humidity suggests airflow review
  - Risks: avoid aggressive or repeated leaf removal that reduces plant vigor; recent leaf pruning should lower urgency
  - Safety: decision_support_only, requires_human_review
- Full ranking highlights:
  - `ventilation_dehumidification` medium confidence=0.5: humidity is high
    - Risks: human review is required before ventilation or dehumidification control changes
    - Safety: decision_support_only, requires_human_review
  - `disease_environment_risk_proxy` medium confidence=0.44: environmental disease risk proxy review, humidity is high
    - Risks: not actual disease prediction without disease labels
    - Safety: decision_support_only, requires_human_review, requires_field_confirmation
  - `leaf_removal_caution` low confidence=0.34: cautious leaf removal review only, leaf density is high, humidity suggests airflow review
    - Risks: avoid aggressive or repeated leaf removal that reduces plant vigor; recent leaf pruning should lower urgency
    - Safety: decision_support_only, requires_human_review
- What-if directions:
  - `ventilation_dehumidification`: humidity may decrease; disease environmental risk may decrease
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
  - `no_action`: current trend likely continues; EC issue remains unresolved; disease environmental risk may remain elevated
    - Assumptions: directional v0 estimate based on literature/manual rules; local calibration and human review are required
    - Warning: This is a what-if scenario estimate, not a validated causal simulation or control command.
