from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from src.backend.extraction.unified_schema import LabelData
from src.backend.extraction.distilled_spirits_label_dataclasses import GOVERNMENT_WARNING_FULL_TEXT

@dataclass
class RulePassInfo:
    rule_id: str
    message: str

@dataclass
class RuleFailInfo:
    rule_id: str
    message: str
    is_hard_failure: bool = False

@dataclass
class RuleUnknownInfo:
    rule_id: str
    message: str
    is_hard_failure: bool = False

@dataclass
class RuleEvaluationResult:
    passed: Dict[str, RulePassInfo] = field(default_factory=dict)
    failed: Dict[str, RuleFailInfo] = field(default_factory=dict)
    unknown: Dict[str, RuleUnknownInfo] = field(default_factory=dict)

class _RuleDictBuilder:
    def __init__(self):
        self.result = RuleEvaluationResult()

    def pass_(self, rule_id: str, message: str) -> None:
        self.result.passed[rule_id] = RulePassInfo(rule_id=rule_id, message=message)

    def fail(self, rule_id: str, message: str, hard_failure: bool = False) -> None:
        self.result.failed[rule_id] = RuleFailInfo(rule_id=rule_id, message=message, is_hard_failure=hard_failure)

    def unknown(self, rule_id: str, message: str, hard_failure: bool = False) -> None:
        self.result.unknown[rule_id] = RuleUnknownInfo(rule_id=rule_id, message=message, is_hard_failure=hard_failure)


def normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    import re
    return re.sub(r'\s+', ' ', text.strip().upper())


def evaluate_rules(label: Optional[LabelData], app: Optional[LabelData]) -> Dict[str, Any]:
    b = _RuleDictBuilder()

    if not label:
        b.fail("DS-LABEL-000", "No label data extracted.", hard_failure=True)
        return {"passed": b.result.passed, "failed": b.result.failed, "unknown": b.result.unknown}

    if not app:
        app = LabelData()

    # BrandName DS-LABEL-001
    l_brand = normalize(label.BrandName)
    a_brand = normalize(app.BrandName)
    if not l_brand:
        b.fail("DS-LABEL-001", "No brand name found on the label.")
    elif a_brand and l_brand != a_brand:
        b.fail("DS-LABEL-001", f"Brand name '{label.BrandName}' does not match application '{app.BrandName}'.")
    else:
        b.pass_("DS-LABEL-001", f"Brand name '{label.BrandName}' matches application.")

    # ClassTypeDesignation DS-LABEL-010
    l_class = normalize(label.ClassTypeDesignation)
    a_class = normalize(app.ClassTypeDesignation)
    if not l_class:
        b.fail("DS-LABEL-010", "No class/type designation found on the label.")
    elif a_class and l_class != a_class:
        b.fail("DS-LABEL-010", f"Class/Type '{label.ClassTypeDesignation}' does not match application '{app.ClassTypeDesignation}'.")
    else:
        b.pass_("DS-LABEL-010", f"Class/Type '{label.ClassTypeDesignation}' matches application.")

    # ABV DS-LABEL-020
    l_abv = normalize(label.ABV)
    a_abv = normalize(app.ABV)
    if not l_abv:
        b.fail("DS-LABEL-020", "No ABV found on the label.")
    elif a_abv and l_abv != a_abv:
        b.fail("DS-LABEL-020", f"ABV '{label.ABV}' does not match application '{app.ABV}'.")
    else:
        b.pass_("DS-LABEL-020", f"ABV '{label.ABV}' matches application.")

    # NetContents DS-LABEL-030
    l_net = normalize(label.NetContents)
    a_net = normalize(app.NetContents)
    if not l_net:
        b.fail("DS-LABEL-030", "No Net Contents found on the label.")
    elif a_net and l_net != a_net:
        b.fail("DS-LABEL-030", f"Net Contents '{label.NetContents}' does not match application '{app.NetContents}'.")
    else:
        b.pass_("DS-LABEL-030", f"Net Contents '{label.NetContents}' matches application.")

    # BottlerProducerNameAddr DS-LABEL-040
    l_bottler = normalize(label.BottlerProducerNameAddr)
    a_bottler = normalize(app.BottlerProducerNameAddr)
    if not l_bottler:
        b.fail("DS-LABEL-040", "No Bottler/Producer info found on the label.")
    elif a_bottler and l_bottler != a_bottler:
        b.fail("DS-LABEL-040", f"Bottler info '{label.BottlerProducerNameAddr}' does not match application '{app.BottlerProducerNameAddr}'.")
    else:
        b.pass_("DS-LABEL-040", f"Bottler info '{label.BottlerProducerNameAddr}' matches application.")

    # ImportOrigin DS-LABEL-050
    l_origin = normalize(label.ImportOrigin)
    a_origin = normalize(app.ImportOrigin)
    if a_origin and l_origin != a_origin:
        b.fail("DS-LABEL-050", f"Import Origin '{label.ImportOrigin}' does not match application '{app.ImportOrigin}'.")
    elif a_origin and l_origin == a_origin:
        b.pass_("DS-LABEL-050", f"Import Origin '{label.ImportOrigin}' matches application.")
    elif l_origin:
        b.pass_("DS-LABEL-050", f"Import Origin found on label: '{label.ImportOrigin}'.")

    # Proof DS-LABEL-060
    l_proof = normalize(label.Proof)
    a_proof = normalize(app.Proof)
    if a_proof and l_proof != a_proof:
        b.fail("DS-LABEL-060", f"Proof '{label.Proof}' does not match application '{app.Proof}'.")
    elif a_proof and l_proof == a_proof:
        b.pass_("DS-LABEL-060", f"Proof '{label.Proof}' matches application.")

    # GovernmentWarningHeaderText DS-LABEL-191
    gov_header = label.GovernmentWarningHeaderText
    if gov_header is None:
        b.fail("DS-LABEL-191", "Missing government warning header.", hard_failure=True)
    elif gov_header.strip() != "GOVERNMENT WARNING:":
        b.fail("DS-LABEL-191", f"Government warning header must be exactly 'GOVERNMENT WARNING:', got '{gov_header}'.", hard_failure=True)
    else:
        b.pass_("DS-LABEL-191", "Government warning header is exactly 'GOVERNMENT WARNING:'.")

    # GovernmentWarningText DS-LABEL-192
    gov_text = normalize(label.GovernmentWarningText)
    req_text = normalize(GOVERNMENT_WARNING_FULL_TEXT)
    if not gov_text:
        b.fail("DS-LABEL-192", "Missing government warning.", hard_failure=True)
    elif req_text not in gov_text:
        b.fail("DS-LABEL-192", f"Government warning text does not match required text. Got: '{label.GovernmentWarningText}'", hard_failure=True)
    else:
        b.pass_("DS-LABEL-192", "Government warning text is exactly correct.")

    def to_dict(obj):
        return {k: v.__dict__ for k, v in obj.items()}

    return {
        "passed": to_dict(b.result.passed),
        "failed": to_dict(b.result.failed),
        "unknown": to_dict(b.result.unknown)
    }
