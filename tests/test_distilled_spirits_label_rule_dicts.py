import pytest
from src.backend.extraction.unified_schema import LabelData
from src.backend.validators.distilled_spirits_label_rule_dicts import evaluate_rules

def test_evaluate_rules_no_label():
    res = evaluate_rules(None, None)
    assert "DS-LABEL-000" in res["failed"]

def test_evaluate_rules_brand_name():
    # Match
    res = evaluate_rules(LabelData(BrandName="Brand A"), LabelData(BrandName="Brand A"))
    assert "DS-LABEL-001" in res["passed"]
    
    # Mismatch
    res = evaluate_rules(LabelData(BrandName="Brand A"), LabelData(BrandName="Brand B"))
    assert "DS-LABEL-001" in res["failed"]
    
    # Missing on label
    res = evaluate_rules(LabelData(BrandName=None), LabelData(BrandName="Brand B"))
    assert "DS-LABEL-001" in res["failed"]

def test_evaluate_rules_abv_llm():
    # Pass
    res = evaluate_rules(LabelData(ABV="40% Alc/Vol", IsABVCorrectLLM=True), LabelData(ABV="40%"))
    assert "DS-LABEL-020" in res["passed"]
    
    # Fail
    res = evaluate_rules(LabelData(ABV="40% Alc/Vol", IsABVCorrectLLM=False), LabelData(ABV="35%"))
    assert "DS-LABEL-020" in res["failed"]
    
    # Missing analysis
    res = evaluate_rules(LabelData(ABV="40% Alc/Vol", IsABVCorrectLLM=None), LabelData(ABV="40%"))
    assert "DS-LABEL-020" in res["failed"]
    assert res["failed"]["DS-LABEL-020"]["message"] == "Missing ABV LLM analysis."

def test_evaluate_rules_government_warning():
    # Pass
    res = evaluate_rules(LabelData(IsGovernmentWarningHeaderCorrectLLM=True, IsGovernmentWarningTextCorrectLLM=True), None)
    assert "DS-LABEL-191" in res["passed"]
    assert "DS-LABEL-192" in res["passed"]
    
    # Fail text
    res = evaluate_rules(LabelData(IsGovernmentWarningHeaderCorrectLLM=True, IsGovernmentWarningTextCorrectLLM=False), None)
    assert "DS-LABEL-191" in res["passed"]
    assert "DS-LABEL-192" in res["failed"]
    
    # Missing analysis
    res = evaluate_rules(LabelData(IsGovernmentWarningHeaderCorrectLLM=None, IsGovernmentWarningTextCorrectLLM=None), None)
    assert "DS-LABEL-191" in res["failed"]
    assert "DS-LABEL-192" in res["failed"]
