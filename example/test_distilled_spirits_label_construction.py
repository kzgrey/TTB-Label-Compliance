from distilled_spirits_label_construction import construct_review_input


def test_construct_review_input_deterministic_smoke():
    app_text = """
    TTB ID: Open help for the TTB ID field in a new window 13221001000316
    Class/Type Code: Open help for the Class/Type Code field in a new window OTHER RUM GOLD USB
    Origin Code: Open help for the Origin Code field in a new window BRAZIL
    Brand Name: Open help for the Brand Name field in a new window SAO PAULO
    Plant Registry/Basic Permit/Brewers No (Principal Place of Business): Open help for the Plant Registry/Basic Permit/Brewers Number field in a new window
    DSP-MD-18
    MONTEBELLO BRANDS, INC.
    1919 WILLOW SPRING RD
    BALTIMORE, MD 21222
    """
    ocr = [
        "SAO PAULO GOLD RUM",
        "PRODUCE OF BRAZIL",
        "40% ALC BY VOL (80 PROOF)",
        "750 mL",
        "IMPORTED BY MONTEBELLO BRANDS, INC. BALTIMORE, MD",
        "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.",
    ]

    result = construct_review_input(application_detail_text=app_text, ocr_text_blocks=ocr)
    review = result.review_input

    assert review.application.application_id == "13221001000316"
    assert review.application.identity.brand_name == "SAO PAULO"
    assert review.application.country_of_origin == "Brazil"
    assert review.label.brand_name.matches_application_brand_name is True
    assert review.label.class_type.matches_application_class_type is True
    assert review.label.alcohol_content.abv_percent == 40.0
    assert review.label.alcohol_content.proof == 80.0
    assert review.label.net_contents.net_contents_ml == 750
    assert review.label.country_of_origin.matches_application_country is True
    assert review.label.government_warning.exact_required_text_present is True
    assert review.checks["DS-LABEL-191.government_warning_exact_text"].state.value == "pass"
