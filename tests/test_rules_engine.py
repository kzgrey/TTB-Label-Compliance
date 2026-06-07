import json
from src.backend.extraction.distilled_spirits_label_construction import construct_review_input
from src.backend.validators.distilled_spirits_label_rule_dicts import build_rule_result_dicts

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
    "GovernmentWarningText": "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS.",
    "ContainerOrLabelCoding": None
  }
}

normalized_blocks = [v for v in llm_json["Label"].values() if isinstance(v, str)]
print("Normalized blocks:", normalized_blocks)

result = construct_review_input(
    application_detail_text="",
    ocr_text_blocks=normalized_blocks,
)

rule_dicts = build_rule_result_dicts(result.review_input)
print("Rule passes:", list(rule_dicts.rule_passes.keys()))
print("Rule fails:", list(rule_dicts.rule_fails.keys()))
