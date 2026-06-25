import unittest

from libsbapi.evidence_rules import (
    EvidenceRuleError,
    auxiliary_alert_rules,
    core_level1_rules,
    evidence_rule_from_json,
    evidence_rules_by_action_type,
    load_evidence_rules,
)


class EvidenceRulesTest(unittest.TestCase):
    LEVEL1_ACTIONS = {
        "irrigation",
        "nutrient_ec_check",
        "ventilation_dehumidification",
        "shading_high_temperature",
        "heating_low_temperature",
    }
    AUXILIARY_ACTIONS = {
        "disease_environment_risk_proxy",
        "harvest_monitoring",
        "leaf_removal_caution",
    }

    def test_loads_required_action_categories(self) -> None:
        rules = load_evidence_rules()
        by_action = evidence_rules_by_action_type(rules)

        self.assertEqual(len(rules), 9)
        self.assertEqual(
            set(by_action),
            {
                "irrigation",
                "nutrient_ec_check",
                "ph_check",
                "ventilation_dehumidification",
                "shading_high_temperature",
                "heating_low_temperature",
                "disease_environment_risk_proxy",
                "harvest_monitoring",
                "leaf_removal_caution",
            },
        )

    def test_all_literature_rules_require_local_calibration(self) -> None:
        rules = load_evidence_rules()

        self.assertTrue(all(rule.needs_local_calibration for rule in rules))
        self.assertTrue(
            all(rule.source_type in {"literature", "manual", "agronomic_assumption", "prototype"} for rule in rules)
        )

    def test_every_level1_action_has_structured_rule_metadata(self) -> None:
        by_action = evidence_rules_by_action_type(load_evidence_rules())

        for action_type in self.LEVEL1_ACTIONS:
            self.assertIn(action_type, by_action)
            self.assertTrue(by_action[action_type], action_type)

        for rule in load_evidence_rules():
            self.assertEqual(rule.rule_id, rule.id)
            self.assertTrue(rule.variable)
            self.assertTrue(rule.condition)
            self.assertTrue(rule.threshold)
            self.assertTrue(rule.unit)
            self.assertIn(rule.confidence_level, {"low", "medium", "high"})
            self.assertTrue(rule.recommendation_effect)
            self.assertTrue(rule.risk_note)
            self.assertIsInstance(rule.growth_stage_scope, tuple)

    def test_prototype_thresholds_are_explicitly_labeled(self) -> None:
        rules = load_evidence_rules()

        prototype_rules = [
            rule for rule in rules
            if "prototype" in rule.threshold.lower() or rule.source_type == "prototype"
        ]

        self.assertTrue(prototype_rules)
        for rule in prototype_rules:
            self.assertTrue(rule.needs_local_calibration)
            self.assertIn(
                "prototype",
                " ".join((rule.source_type, rule.threshold, rule.source_note)).lower(),
            )

    def test_auxiliary_alert_rules_are_not_core_level1_by_default(self) -> None:
        rules = load_evidence_rules()
        core_actions = {rule.action_type for rule in core_level1_rules(rules)}
        auxiliary_actions = {rule.action_type for rule in auxiliary_alert_rules(rules)}

        self.assertEqual(core_actions, self.LEVEL1_ACTIONS)
        self.assertEqual(auxiliary_actions, self.AUXILIARY_ACTIONS)
        self.assertFalse(core_actions & auxiliary_actions)

    def test_disease_and_leaf_rules_keep_required_cautions(self) -> None:
        by_action = evidence_rules_by_action_type(load_evidence_rules())
        disease_rule = by_action["disease_environment_risk_proxy"][0]
        leaf_rule = by_action["leaf_removal_caution"][0]

        self.assertIn("environmental disease-risk proxy", disease_rule.condition_description)
        self.assertIn("not actual disease prediction", disease_rule.risk_or_caution)
        self.assertIn("Excessive leaf removal", leaf_rule.risk_or_caution)
        self.assertIn("downgrade recommendation", leaf_rule.threshold_or_range)

    def test_rejects_incomplete_evidence_rule(self) -> None:
        with self.assertRaises(EvidenceRuleError):
            evidence_rule_from_json(
                {
                    "id": "bad.rule",
                    "action_type": "irrigation",
                    "condition_variables": [],
                    "condition_description": "missing usable variables",
                    "threshold_or_range": "none",
                    "expected_effect": "none",
                    "risk_or_caution": "none",
                    "evidence_level": "literature_assumption",
                    "source_title": "test",
                    "source_note": "test",
                    "needs_local_calibration": True,
                }
            )


if __name__ == "__main__":
    unittest.main()
