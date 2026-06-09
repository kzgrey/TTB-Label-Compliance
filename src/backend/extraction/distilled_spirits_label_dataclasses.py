"""
Dataclasses for a distilled-spirits label validator.

The image/OCR layer should populate DistilledSpiritsLabelReviewInput.label.
The application/COLA layer should populate DistilledSpiritsLabelReviewInput.application.
The validator should consume the combined object and emit rule outcomes.

Out of scope by request: text size, color/background contrast, and field positioning.
Kept as in-scope: exact required wording, ABV/net-contents values, required disclosures,
health-warning capitalization/bold/continuous-paragraph facts, and product/application facts
that determine whether conditional fields are required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class StrEnum(str, Enum):
    """Small Python 3.10-compatible StrEnum."""

    def __str__(self) -> str:
        return self.value


class ContainerKind(StrEnum):
    NON_CAN = "non_can"
    CAN = "can"


class ImportStatus(StrEnum):
    DOMESTIC = "domestic"
    IMPORTED_BOTTLED_BEFORE_IMPORTATION = "imported_bottled_before_importation"
    IMPORTED_BOTTLED_AFTER_IMPORTATION = "imported_bottled_after_importation"


class ResponsiblePartyRole(StrEnum):
    BOTTLER = "bottler"
    PACKER = "packer"
    FILLER = "filler"
    DISTILLER = "distiller"
    BLENDER = "blender"
    MAKER = "maker"
    PREPARER = "preparer"
    MANUFACTURER = "manufacturer"
    PRODUCER = "producer"
    IMPORTER = "importer"
    SOLE_AGENT = "sole_agent"


class CommodityStatementGroup(StrEnum):
    NONE = "none"
    GROUP_1_PERCENT_AND_COMMODITY = "group_1_percent_and_commodity"
    GROUP_2_COMMODITY_ONLY = "group_2_commodity_only"


class NeutralSpiritDistillationMethod(StrEnum):
    ORIGINAL_DISTILLATION = "original_distillation"
    REDISTILLATION = "redistillation"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ComplianceState(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


GOVERNMENT_WARNING_HEADER = "GOVERNMENT WARNING"
GOVERNMENT_WARNING_BODY = (
    "(1) According to the Surgeon General, women should not drink alcoholic beverages "
    "during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic "
    "beverages impairs your ability to drive a car or operate machinery, and may cause "
    "health problems."
)
GOVERNMENT_WARNING_FULL_TEXT = f"{GOVERNMENT_WARNING_HEADER}: {GOVERNMENT_WARNING_BODY}"

SACCHARIN_DISCLOSURE_TEXT = (
    "USE OF THIS PRODUCT MAY BE HAZARDOUS TO YOUR HEALTH. THIS PRODUCT CONTAINS "
    "SACCHARIN WHICH HAS BEEN DETERMINED TO CAUSE CANCER IN LABORATORY ANIMALS."
)

NON_CAN_STANDARD_FILLS_ML = frozenset({1750, 1000, 750, 375, 200, 100, 50})
CAN_STANDARD_FILLS_ML = frozenset({355, 200, 100, 50})

# Types listed in the manual/state-of-distillation rules for U.S.-produced whisky.
STATE_OF_DISTILLATION_WHISKY_TYPES = frozenset(
    {
        "bourbon whisky",
        "rye whisky",
        "wheat whisky",
        "malt whisky",
        "rye malt whisky",
        "corn whisky",
        "straight bourbon whisky",
        "straight rye whisky",
        "straight wheat whisky",
        "straight malt whisky",
        "straight rye malt whisky",
        "straight corn whisky",
        "straight whisky",
        "whisky distilled from bourbon mash",
        "whisky distilled from rye mash",
        "whisky distilled from wheat mash",
        "whisky distilled from malt mash",
        "whisky distilled from rye malt mash",
    }
)


@dataclass
class Check:
    """Optional precomputed assertion from OCR/extraction or validator."""

    state: ComplianceState = ComplianceState.UNKNOWN
    confidence: float | None = None
    reason: str | None = None
    rule_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_bool(
        cls,
        value: bool | None,
        *,
        confidence: float | None = None,
        reason: str | None = None,
        rule_ids: list[str] | None = None,
    ) -> "Check":
        if value is True:
            state = ComplianceState.PASS
        elif value is False:
            state = ComplianceState.FAIL
        else:
            state = ComplianceState.UNKNOWN
        return cls(state=state, confidence=confidence, reason=reason, rule_ids=rule_ids or [])


@dataclass
class ExtractedText:
    """Raw text plus normalized value and model confidence for one label field."""

    text: str | None = None
    normalized_text: str | None = None
    confidence: float | None = None
    language: str | None = None
    notes: str | None = None

    @property
    def is_present(self) -> bool:
        return bool(self.text and self.text.strip())


@dataclass
class Address:
    company_name: str | None = None
    trade_name: str | None = None
    street: str | None = None
    city: str | None = None
    state_or_province: str | None = None
    postal_code: str | None = None
    country: str | None = None


@dataclass
class ResponsiblePartyApplication:
    role: ResponsiblePartyRole
    name: str
    address: Address
    basic_permit_name: str | None = None
    basic_permit_address: Address | None = None
    uses_principal_place_of_business: bool | None = None
    actual_operation_address_marked_on_label_or_container: bool | None = None


@dataclass
class WineAdditionFacts:
    """Facts needed for flavored spirits with added wine."""

    wine_class_type: str | None = None
    percent_by_volume_of_finished_product: float | None = None
    percent_of_wine_from_base_commodity: float | None = None


@dataclass
class ComponentPercentage:
    name: str
    percent: float | None = None
    country_or_origin: str | None = None
    proof_gallon_basis: bool = True


@dataclass
class ProductIdentityApplication:
    brand_name: str | None = None
    not_sold_under_brand_name: bool = False

    # Canonical class/type from the application and/or product facts.
    class_name: str | None = None
    type_name: str | None = None
    class_type_designation: str | None = None
    class_or_type_name_is_sufficient_designation: bool | None = None
    minimum_bottled_abv_for_class_type: float | None = None
    required_country_or_region_for_class_type: str | None = None

    # Special class/type cases from the rules workbook/manual.
    is_distilled_spirits_specialty: bool = False
    is_imitation: bool = False
    imitation_base_class_type: str | None = None
    is_recognized_cocktail: bool = False
    recognized_cocktail_name: str | None = None
    distilled_spirit_components: list[str] = field(default_factory=list)

    is_flavored: bool = False
    flavored_base_class_type: str | None = None  # e.g. flavored vodka, flavored rum.
    predominant_flavor: str | None = None
    wine_addition: WineAdditionFacts | None = None

    is_creme_de: bool = False
    creme_de_flavor: str | None = None
    is_compounded_gin: bool = False

    # Region/term-specific facts.
    uses_sambuca_term: bool = False
    uses_goldwasser_term: bool = False
    uses_arak_arack_or_raki_term: bool = False
    sugar_dextrose_levulose_percent_by_weight: float | None = None
    produced_country: str | None = None
    produced_region: str | None = None

    # Brandy/fruit-brandy special designation facts.
    is_brandy: bool = False
    brandy_base_fruit: str | None = None  # None or "grape" for plain Brandy.
    brandy_components: list[ComponentPercentage] = field(default_factory=list)
    fruit_brandy_fruits: list[ComponentPercentage] = field(default_factory=list)

    # Whisky origin/blending facts.
    is_whisky: bool = False
    is_us_produced_whisky: bool = False
    domestic_and_imported_whisky_components: list[ComponentPercentage] = field(default_factory=list)


@dataclass
class AlcoholApplication:
    abv_percent: float | None = None
    proof: float | None = None
    contains_solid_material: bool = False
    solids_mg_per_100ml: float | None = None
    bottling_loss_abv_percent: float | None = None

    def allowed_abv_tolerance_percent(self, net_contents_ml: int | None) -> float | None:
        """Tolerance used by the validator when comparing application ABV to label ABV."""
        if self.abv_percent is None:
            return None
        if self.solids_mg_per_100ml is not None and self.solids_mg_per_100ml > 600:
            return 0.25
        if net_contents_ml in {50, 100}:
            return 0.25
        return 0.15


@dataclass
class NetContentsApplication:
    net_contents_ml: int | None = None
    container_kind: ContainerKind = ContainerKind.NON_CAN
    bottled_or_packed_date: date | None = None

    def is_standard_fill(self) -> bool | None:
        if self.net_contents_ml is None:
            return None
        allowed = CAN_STANDARD_FILLS_ML if self.container_kind == ContainerKind.CAN else NON_CAN_STANDARD_FILLS_ML
        return self.net_contents_ml in allowed


@dataclass
class DisclosureApplication:
    contains_coloring_materials: bool = False
    coloring_materials: list[str] = field(default_factory=list)
    coloring_material_changes_class_type: bool | None = None

    treated_with_wood_other_than_oak_container_contact: bool = False
    wood_treatment_form: str | None = None  # chips, slabs, extracts, etc.
    wood_treatment_exception_applies: bool | None = None

    contains_fdc_yellow_5: bool = False
    contains_saccharin: bool = False
    sulfur_dioxide_ppm: float | None = None
    sulfiting_agents: list[str] = field(default_factory=list)

    @property
    def contains_sulfites_at_declaration_threshold(self) -> bool | None:
        if self.sulfur_dioxide_ppm is None:
            return None
        return self.sulfur_dioxide_ppm >= 10


@dataclass()
class CommodityStatementApplication:
    group: CommodityStatementGroup = CommodityStatementGroup.NONE
    neutral_spirits_percent: float | None = None
    neutral_spirit_commodity: str | None = None
    neutral_spirit_distillation_method: NeutralSpiritDistillationMethod = NeutralSpiritDistillationMethod.NOT_APPLICABLE


@dataclass()
class AgeComponentApplication:
    class_type: str
    percent_proof_gallon_basis: float | None = None
    age_months: int | None = None
    is_straight_whisky: bool | None = None
    is_neutral_spirit: bool = False


@dataclass()
class AgeApplication:
    actual_age_months: int | None = None
    youngest_component_age_months: int | None = None

    # Trigger facts.
    is_any_whisky_type: bool = False
    is_grape_lees_brandy: bool = False
    is_grape_pomace_or_marc_brandy: bool = False
    label_has_misc_age_reference_or_representation: bool | None = None
    label_has_distillation_date: bool | None = None

    # Format/exception facts.
    us_whisky_stored_in_reused_oak_containers: bool = False
    whisky_contains_neutral_spirits: bool = False
    components: list[AgeComponentApplication] = field(default_factory=list)
    specific_age_statement_allowed_for_class_type: bool | None = None
    misc_age_reference_allowed_for_class_type: bool | None = None
    distillation_date_allowed_for_class_type: bool | None = None

    def age_statement_required_by_age(self) -> bool | None:
        age = self.youngest_component_age_months if self.youngest_component_age_months is not None else self.actual_age_months
        if age is None:
            return None
        if self.is_any_whisky_type and age < 48:
            return True
        if (self.is_grape_lees_brandy or self.is_grape_pomace_or_marc_brandy) and age < 24:
            return True
        return False


@dataclass()
class StateOfDistillationApplication:
    produced_in_united_states: bool = False
    whisky_type: str | None = None
    actual_state_of_distillation: str | None = None
    state_in_name_address_statement: str | None = None
    label_may_mislead_about_state: bool | None = None

    # Set by application ingest if the UI/COLA data already knows the disclosure is required.
    # This avoids making the OCR dataclass depend on label placement, which is out of scope.
    state_of_distillation_statement_required: bool | None = None

    @property
    def is_covered_us_whisky_type(self) -> bool:
        return (
            self.produced_in_united_states
            and self.whisky_type is not None
            and self.whisky_type.strip().lower() in STATE_OF_DISTILLATION_WHISKY_TYPES
        )


@dataclass()
class SaleApplication:
    for_sale_or_distribution_in_us: bool = True
    intended_for_human_consumption: bool = True
    bottled_on_or_after_1989_11_18: bool = True


@dataclass()
class DistilledSpiritsApplication:
    """Application/COLA facts the label must match."""

    application_id: str | None = None
    identity: ProductIdentityApplication = field(default_factory=ProductIdentityApplication)
    alcohol: AlcoholApplication = field(default_factory=AlcoholApplication)
    net_contents: NetContentsApplication = field(default_factory=NetContentsApplication)
    import_status: ImportStatus = ImportStatus.DOMESTIC
    country_of_origin: str | None = None
    responsible_parties: list[ResponsiblePartyApplication] = field(default_factory=list)
    disclosures: DisclosureApplication = field(default_factory=DisclosureApplication)
    commodity_statement: CommodityStatementApplication = field(default_factory=CommodityStatementApplication)
    age: AgeApplication = field(default_factory=AgeApplication)
    state_of_distillation: StateOfDistillationApplication = field(default_factory=StateOfDistillationApplication)
    sale: SaleApplication = field(default_factory=SaleApplication)
    extra_application_facts: dict[str, Any] = field(default_factory=dict)

    def government_warning_required(self) -> bool:
        return (
            self.sale.for_sale_or_distribution_in_us
            and self.sale.intended_for_human_consumption
            and self.sale.bottled_on_or_after_1989_11_18
            and self.alcohol.abv_percent is not None
            and self.alcohol.abv_percent >= 0.5
        )


@dataclass()
class BrandNameLabel:
    value: ExtractedText = field(default_factory=ExtractedText)
    matches_application_brand_name: bool | None = None
    responsible_party_used_as_brand_when_no_brand: bool | None = None
    describes_age_origin_identity_or_characteristics: bool | None = None
    accurately_describes_product: bool | None = None
    conveys_erroneous_impression: bool | None = None
    qualified_with_brand_word: bool | None = None


@dataclass()
class ClassTypeDesignationLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    declared_class: str | None = None
    declared_type: str | None = None
    matches_application_class_type: bool | None = None
    class_or_type_name_is_sufficient: bool | None = None

    # Conditional designation facts.
    specialty_statement_of_composition_present: bool | None = None
    imitation_designation_present: bool | None = None
    cocktail_component_declaration_present: bool | None = None
    predominant_flavor_declared: bool | None = None
    wine_class_type_and_percent_declared: bool | None = None
    foreign_whisky_origin_qualifier_present: bool | None = None
    domestic_foreign_whisky_percent_origin_declared: bool | None = None
    compounded_gin_improperly_described_as_distilled: bool | None = None
    brandy_fruit_or_component_percentages_compliant: bool | None = None
    sambuca_or_goldwasser_origin_qualifier_present: bool | None = None
    arak_arack_raki_specialty_composition_statement_present: bool | None = None
    minimum_abv_for_class_type_satisfied: bool | None = None
    required_origin_for_class_type_satisfied: bool | None = None


@dataclass()
class AlcoholContentLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    abv_percent: float | None = None
    proof: float | None = None
    has_percent_alcohol_by_volume_phrase: bool | None = None
    uses_bottled_at_phrase_for_products_with_solids: bool | None = None
    matches_application_abv_with_tolerance: bool | None = None
    proof_is_distinguished_from_abv_statement: bool | None = None


@dataclass()
class NetContentsLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    net_contents_ml: int | None = None
    matches_application_net_contents: bool | None = None
    is_metric_standard_of_fill: bool | None = None


@dataclass()
class ResponsiblePartyLabelStatement:
    statement: ExtractedText = field(default_factory=ExtractedText)
    role_phrase: str | None = None
    roles: list[ResponsiblePartyRole] = field(default_factory=list)
    name: str | None = None
    address: Address | None = None

    phrase_is_appropriate: bool | None = None
    name_matches_basic_permit_or_application: bool | None = None
    address_matches_basic_permit_or_application: bool | None = None
    us_bottling_packing_or_filling_indicated_for_import: bool | None = None
    actual_operation_address_code_present_when_required: bool | None = None


@dataclass()
class CountryOfOriginLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    country: str | None = None
    matches_application_country: bool | None = None
    accepted_format: bool | None = None


@dataclass()
class ColoringDisclosureLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    disclosed_materials: list[str] = field(default_factory=list)
    uses_artificially_colored_phrase: bool | None = None
    discloses_required_coloring_materials: bool | None = None
    class_type_reflects_materials_when_materials_change_class_type: bool | None = None


@dataclass()
class WoodTreatmentDisclosureLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    wood_form: str | None = None
    contains_colored_and_flavored_with_wood_phrase: bool | None = None
    exception_applies: bool | None = None


@dataclass()
class FdcYellow5DisclosureLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    contains_required_phrase: bool | None = None


@dataclass()
class SaccharinDisclosureLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    exact_required_text_present: bool | None = None


@dataclass()
class SulfiteDeclarationLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    contains_sulfites_phrase_present: bool | None = None
    contains_sulfiting_agents_phrase_present: bool | None = None
    specific_sulfiting_agents_declared: bool | None = None


@dataclass()
class CommodityStatementLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    detected_group: CommodityStatementGroup | None = None
    neutral_spirits_percent: float | None = None
    neutral_spirit_commodity: str | None = None
    group1_percent_and_commodity_present: bool | None = None
    group2_distilled_from_commodity_present: bool | None = None
    matches_application_commodity: bool | None = None
    matches_application_neutral_spirits_percent: bool | None = None


@dataclass()
class AgeStatementComponentLabel:
    class_type: str | None = None
    percent_proof_gallon_basis: float | None = None
    age_months: int | None = None
    raw_text: str | None = None


@dataclass()
class AgeStatementLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    stated_age_months: int | None = None
    components: list[AgeStatementComponentLabel] = field(default_factory=list)
    uses_years_old_or_aged_years_format: bool | None = None
    uses_reused_cooperage_format: bool | None = None
    whisky_neutral_spirits_age_and_percent_statement_present: bool | None = None
    percentages_total_100_when_required: bool | None = None
    age_is_not_overstated: bool | None = None
    required_age_statement_present: bool | None = None


@dataclass()
class StateOfDistillationLabel:
    statement: ExtractedText = field(default_factory=ExtractedText)
    state: str | None = None
    accepted_format: bool | None = None
    matches_application_state: bool | None = None


@dataclass()
class GovernmentWarningLabel:
    full_text: ExtractedText = field(default_factory=ExtractedText)
    header_text: ExtractedText = field(default_factory=ExtractedText)
    body_text: ExtractedText = field(default_factory=ExtractedText)

    header_is_exact_all_caps: bool | None = None
    header_is_bold: bool | None = None
    body_is_not_bold: bool | None = None
    exact_required_text_present: bool | None = None
    appears_as_continuous_paragraph: bool | None = None

    # Example of a resolved boolean intended for the downstream validator.
    government_warning_compliant: bool | None = None


@dataclass()
class DistilledSpiritsLabelExtraction:
    """All required or conditionally required distilled-spirits label fields."""

    brand_name: BrandNameLabel = field(default_factory=BrandNameLabel)
    class_type: ClassTypeDesignationLabel = field(default_factory=ClassTypeDesignationLabel)
    alcohol_content: AlcoholContentLabel = field(default_factory=AlcoholContentLabel)
    net_contents: NetContentsLabel = field(default_factory=NetContentsLabel)
    responsible_party_statements: list[ResponsiblePartyLabelStatement] = field(default_factory=list)
    country_of_origin: CountryOfOriginLabel = field(default_factory=CountryOfOriginLabel)

    coloring_disclosure: ColoringDisclosureLabel = field(default_factory=ColoringDisclosureLabel)
    wood_treatment_disclosure: WoodTreatmentDisclosureLabel = field(default_factory=WoodTreatmentDisclosureLabel)
    fdc_yellow_5_disclosure: FdcYellow5DisclosureLabel = field(default_factory=FdcYellow5DisclosureLabel)
    saccharin_disclosure: SaccharinDisclosureLabel = field(default_factory=SaccharinDisclosureLabel)
    sulfite_declaration: SulfiteDeclarationLabel = field(default_factory=SulfiteDeclarationLabel)
    commodity_statement: CommodityStatementLabel = field(default_factory=CommodityStatementLabel)
    age_statement: AgeStatementLabel = field(default_factory=AgeStatementLabel)
    state_of_distillation: StateOfDistillationLabel = field(default_factory=StateOfDistillationLabel)
    government_warning: GovernmentWarningLabel = field(default_factory=GovernmentWarningLabel)

    # Label-level facts from image/OCR that may trigger conditional requirements.
    has_misc_age_reference_or_representation: bool | None = None
    has_distillation_date: bool | None = None
    distillation_date_text: ExtractedText = field(default_factory=ExtractedText)
    label_may_mislead_about_state_of_distillation: bool | None = None

    # Useful for debugging and later rule expansion; validator should not depend on it for known fields.
    all_detected_text: list[ExtractedText] = field(default_factory=list)
    overall_extraction_confidence: float | None = None
    extraction_notes: str | None = None
    extra_extracted_facts: dict[str, Any] = field(default_factory=dict)


@dataclass()
class DistilledSpiritsLabelReviewInput:
    """Top-level object passed into the validator."""

    application: DistilledSpiritsApplication
    label: DistilledSpiritsLabelExtraction
    source_image_id: str | None = None
    source_filename: str | None = None

    # Optional precomputed checks. A validator can fill this in after evaluation,
    # or the extraction step can pre-populate deterministic checks such as exact text matches.
    checks: dict[str, Check] = field(default_factory=dict)


# Minimal example payload shape. Remove or move to tests in production.
EXAMPLE_REVIEW_INPUT = DistilledSpiritsLabelReviewInput(
    application=DistilledSpiritsApplication(
        identity=ProductIdentityApplication(
            brand_name="OLD TOM DISTILLERY",
            class_type_designation="Kentucky Straight Bourbon Whiskey",
            type_name="straight bourbon whisky",
            is_whisky=True,
            is_us_produced_whisky=True,
        ),
        alcohol=AlcoholApplication(abv_percent=45.0, proof=90.0),
        net_contents=NetContentsApplication(net_contents_ml=750),
        responsible_parties=[
            ResponsiblePartyApplication(
                role=ResponsiblePartyRole.BOTTLER,
                name="Old Tom Distillery",
                address=Address(city="Louisville", state_or_province="KY", country="United States"),
            )
        ],
    ),
    label=DistilledSpiritsLabelExtraction(
        brand_name=BrandNameLabel(value=ExtractedText(text="OLD TOM DISTILLERY")),
        class_type=ClassTypeDesignationLabel(
            statement=ExtractedText(text="Kentucky Straight Bourbon Whiskey"),
            declared_type="straight bourbon whisky",
            matches_application_class_type=True,
        ),
        alcohol_content=AlcoholContentLabel(
            statement=ExtractedText(text="45% Alc./Vol. (90 Proof)"),
            abv_percent=45.0,
            proof=90.0,
            has_percent_alcohol_by_volume_phrase=True,
            matches_application_abv_with_tolerance=True,
        ),
        net_contents=NetContentsLabel(
            statement=ExtractedText(text="750 mL"),
            net_contents_ml=750,
            matches_application_net_contents=True,
            is_metric_standard_of_fill=True,
        ),
        government_warning=GovernmentWarningLabel(
            full_text=ExtractedText(text=GOVERNMENT_WARNING_FULL_TEXT),
            header_text=ExtractedText(text=GOVERNMENT_WARNING_HEADER),
            body_text=ExtractedText(text=GOVERNMENT_WARNING_BODY),
            header_is_exact_all_caps=True,
            header_is_bold=True,
            body_is_not_bold=True,
            exact_required_text_present=True,
            appears_as_continuous_paragraph=True,
            government_warning_compliant=True,
        ),
    ),
)
