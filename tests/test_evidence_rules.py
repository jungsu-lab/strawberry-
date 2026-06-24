import unittest

from libsbapi.evidence_rules import (
    EvidenceRuleError,
    evidence_rule_from_json,
    evidence_rules_by_action_type,
    load_evidence_rules,
)


class EvidenceRulesTest(unittest.TestCase):
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
            all(rule.evidence_level in {"literature_assumption", "manual_assumption"} for rule in rules)
        )

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
