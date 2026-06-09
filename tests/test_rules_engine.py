import json
from src.backend.extraction.distilled_spirits_label_construction import construct_review_input
from src.backend.validators.distilled_spirits_label_rule_dicts import evaluate_rules
from src.backend.extraction.unified_schema import LabelData

def test_rules_engine_example():
    llm_json = {
      "Label": {
        "BrandName": "Bärenjäger",
        "ClassTypeDesignation": "HONEY LIQUEUR",
        "ABV": "35% ALC. BY VOL",
        "NetContents": "50ML",
        "BottlerProducerNameAddr": "PRODUCED AND BOTTLED IN GERMANY",
        "ImportOrigin": "IMPORTED BY SIDNEY FRANK IMPORTING CO., INC. NEW ROCHELLE, N.Y.",
        "FancifulName": None,
        "WhiskyDesignation": None,
        "Proof": None,
        "ColoringMaterialDisclosure": "CARAMEL COLOR ADDED",
        "ForeignComponentPercentagesAndOrigins": None,
        "RuleSpecificFact": "SMALL CLUSTERS MAY FORM FROM NATURAL HONEY CONTENT. PLEASE SHAKE BOTTLE TO CLEAR.",
        "PercentageAndName": None,
        "ContainerEmbossedText": None,
        "IsGovernmentWarningTextCorrectLLM": True,
        "IsGovernmentWarningHeaderCorrectLLM": True,
        "IsABVCorrectLLM": True,
        "ContainerOrLabelCoding": None
      }
    }
    
    label_data = LabelData(**llm_json["Label"])
    app_data = LabelData(
        BrandName="Bärenjäger", 
        ClassTypeDesignation="HONEY LIQUEUR", 
        ABV="35%", 
        NetContents="50ML",
        BottlerProducerNameAddr="PRODUCED AND BOTTLED IN GERMANY",
    )
    
    rule_dicts = evaluate_rules(label_data, app_data)
    
    assert "DS-LABEL-001" in rule_dicts["passed"]
    assert "DS-LABEL-010" in rule_dicts["passed"]
    assert "DS-LABEL-020" in rule_dicts["passed"]
    assert "DS-LABEL-191" in rule_dicts["passed"]
