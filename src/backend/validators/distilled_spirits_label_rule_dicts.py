"""Rule-result dictionaries for distilled-spirits label validation.

The construction layer produces a DistilledSpiritsLabelReviewInput.  This module
consumes that dataclass and emits exactly the three dictionaries requested by the
validator/UI layer:

    rule_passes:  {rule_id: reason}
    rule_fails:   {rule_id: reason}
    rule_unknown: {rule_id: {"reason": reason, "hard_failure": bool}}

`hard_failure` on an unknown means the missing/ambiguous fact should block an
automated compliant result until the fact is supplied.  It does not necessarily
mean the label should be rejected by a human reviewer.

Out of scope by project requirement: text size, color/background contrast, and
physical label positioning.  Rules that only test those concerns are intentionally
not emitted as pass/fail/unknown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict
try:
    from typing import TypeAlias
except ImportError:
    TypeAlias = Any

from src.backend.extraction import distilled_spirits_label_dataclasses as ds


RulePassesDict: TypeAlias = dict[str, str]
"""key: rule id; value: why the rule passed."""

RuleFailsDict: TypeAlias = dict[str, str]
"""key: rule id; value: why the rule failed."""


class UnknownRuleDetail(TypedDict):
    """Serializable value for RuleUnknownDict."""

    reason: str
    hard_failure: bool


RuleUnknownDict: TypeAlias = dict[str, UnknownRuleDetail]
"""key: rule id; value: why the rule is unknown and whether that unknown blocks auto-pass."""


@dataclass(slots=True)
class RuleEvaluationDicts:
    """Container for the three rule dictionaries."""

    rule_passes: RulePassesDict = field(default_factory=dict)
    rule_fails: RuleFailsDict = field(default_factory=dict)
    rule_unknown: RuleUnknownDict = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_passes": dict(sorted(self.rule_passes.items())),
            "rule_fails": dict(sorted(self.rule_fails.items())),
            "rule_unknown": {k: self.rule_unknown[k] for k in sorted(self.rule_unknown)},
        }


# Rules intentionally ignored because they are only or primarily type size,
# color/background contrast, legibility, physical placement, or characters-per-inch.
# The take-home scope excludes those concerns.
OUT_OF_SCOPE_RULE_IDS: frozenset[str] = frozenset(
    {
        "DS-LABEL-004",
        "DS-LABEL-005",
        "DS-LABEL-014",
        "DS-LABEL-015",
        "DS-LABEL-016",
        "DS-LABEL-046",
        "DS-LABEL-047",
        "DS-LABEL-056",
        "DS-LABEL-057",
        "DS-LABEL-067",
        "DS-LABEL-068",
        "DS-LABEL-077",
        "DS-LABEL-078",
        "DS-LABEL-079",
        "DS-LABEL-087",
        "DS-LABEL-089",
        "DS-LABEL-090",
        "DS-LABEL-091",
        "DS-LABEL-092",
        "DS-LABEL-103",
        "DS-LABEL-104",
        "DS-LABEL-105",
        "DS-LABEL-113",
        "DS-LABEL-114",
        "DS-LABEL-115",
        "DS-LABEL-122",
        "DS-LABEL-123",
        "DS-LABEL-132",
        "DS-LABEL-133",
        "DS-LABEL-142",
        "DS-LABEL-143",
        "DS-LABEL-144",
        "DS-LABEL-158",
        "DS-LABEL-159",
        "DS-LABEL-170",
        "DS-LABEL-174",
        "DS-LABEL-176",
        "DS-LABEL-177",
        "DS-LABEL-178",
        "DS-LABEL-179",
        "DS-LABEL-182",
        "DS-LABEL-187",
        "DS-LABEL-188",
        "DS-LABEL-195",
        "DS-LABEL-196",
        "DS-LABEL-197",
        "DS-LABEL-198",
    }
)


DOMESTIC_RESPONSIBLE_ROLES: frozenset[ds.ResponsiblePartyRole] = frozenset(
    {
        ds.ResponsiblePartyRole.BOTTLER,
        ds.ResponsiblePartyRole.PACKER,
        ds.ResponsiblePartyRole.FILLER,
        ds.ResponsiblePartyRole.DISTILLER,
        ds.ResponsiblePartyRole.BLENDER,
        ds.ResponsiblePartyRole.MAKER,
        ds.ResponsiblePartyRole.PREPARER,
        ds.ResponsiblePartyRole.MANUFACTURER,
        ds.ResponsiblePartyRole.PRODUCER,
    }
)

IMPORTED_BEFORE_ROLES: frozenset[ds.ResponsiblePartyRole] = frozenset(
    {ds.ResponsiblePartyRole.IMPORTER, ds.ResponsiblePartyRole.SOLE_AGENT}
)

IMPORTED_AFTER_ROLES: frozenset[ds.ResponsiblePartyRole] = frozenset(
    {
        ds.ResponsiblePartyRole.IMPORTER,
        ds.ResponsiblePartyRole.BOTTLER,
        ds.ResponsiblePartyRole.PACKER,
        ds.ResponsiblePartyRole.FILLER,
    }
)

US_COUNTRY_NAMES: frozenset[str] = frozenset(
    {
        "united states",
        "united states of america",
        "usa",
        "u.s.a.",
        "u.s.",
        "us",
        "america",
    }
)

WHISKY_WORDS: tuple[str, ...] = ("whisky", "whiskey")


class _RuleDictBuilder:
    def __init__(self) -> None:
        self.result = RuleEvaluationDicts()

    def pass_(self, rule_id: str, reason: str) -> None:
        if rule_id in OUT_OF_SCOPE_RULE_IDS:
            return
        self._clear(rule_id)
        self.result.rule_passes[rule_id] = reason

    def fail(self, rule_id: str, reason: str) -> None:
        if rule_id in OUT_OF_SCOPE_RULE_IDS:
            return
        self._clear(rule_id)
        self.result.rule_fails[rule_id] = reason

    def unknown(self, rule_id: str, reason: str, *, hard_failure: bool) -> None:
        if rule_id in OUT_OF_SCOPE_RULE_IDS:
            return
        self._clear(rule_id)
        self.result.rule_unknown[rule_id] = {"reason": reason, "hard_failure": hard_failure}

    def bool_rule(
        self,
        rule_id: str,
        value: bool | None,
        *,
        pass_reason: str,
        fail_reason: str,
        unknown_reason: str,
        hard_failure: bool = True,
    ) -> None:
        if value is True:
            self.pass_(rule_id, pass_reason)
        elif value is False:
            self.fail(rule_id, fail_reason)
        else:
            self.unknown(rule_id, unknown_reason, hard_failure=hard_failure)

    def _clear(self, rule_id: str) -> None:
        self.result.rule_passes.pop(rule_id, None)
        self.result.rule_fails.pop(rule_id, None)
        self.result.rule_unknown.pop(rule_id, None)


def build_rule_result_dicts(review: ds.DistilledSpiritsLabelReviewInput) -> RuleEvaluationDicts:
    """Evaluate in-scope distilled-spirits rules into pass/fail/unknown dictionaries.

    The evaluator is intentionally conservative about facts that cannot be recovered
    from OCR text blocks or the pasted application detail.  Unknown facts are kept in
    `rule_unknown` rather than guessed.
    """

    b = _RuleDictBuilder()
    _evaluate_brand_rules(b, review)
    _evaluate_class_type_rules(b, review)
    _evaluate_responsible_party_rules(b, review)
    _evaluate_country_of_origin_rules(b, review)
    _evaluate_net_contents_rules(b, review)
    _evaluate_alcohol_content_rules(b, review)
    _evaluate_disclosure_rules(b, review)
    _evaluate_commodity_statement_rules(b, review)
    _evaluate_age_statement_rules(b, review)
    _evaluate_state_of_distillation_rules(b, review)
    _evaluate_government_warning_rules(b, review)
    return b.result


# Backwards-friendly alias for callers who prefer "evaluate" wording.
evaluate_rule_dicts = build_rule_result_dicts


# ---------------------------------------------------------------------------
# Individual rule groups
# ---------------------------------------------------------------------------


def _evaluate_brand_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    brand = label.brand_name
    brand_text = _clean(brand.value.text)
    app_brand = _clean(app.identity.brand_name)

    if not brand_text:
        b.fail("DS-LABEL-001", "No brand name was extracted from the OCR text blocks.")
    elif app_brand and brand.matches_application_brand_name is False:
        b.fail(
            "DS-LABEL-001",
            f"Brand name was extracted as {_q(brand_text)}, but it does not match application brand {_q(app_brand)}.",
        )
    elif app_brand and brand.matches_application_brand_name is None:
        b.unknown(
            "DS-LABEL-001",
            f"Brand name was extracted as {_q(brand_text)}, but the application brand match against {_q(app_brand)} was not resolved.",
            hard_failure=True,
        )
    else:
        match_suffix = f" and matches application brand {_q(app_brand)}" if app_brand else ""
        b.pass_("DS-LABEL-001", f"Brand name was extracted as {_q(brand_text)}{match_suffix}.")

    if app.identity.not_sold_under_brand_name:
        b.bool_rule(
            "DS-LABEL-002",
            brand.responsible_party_used_as_brand_when_no_brand,
            pass_reason="Application indicates no marketed brand name, and the responsible party was resolved as the label brand.",
            fail_reason="Application indicates no marketed brand name, but the responsible party was not resolved as the label brand.",
            unknown_reason="Application indicates no marketed brand name, but OCR/LLM output did not resolve whether the responsible party should be treated as the brand.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-002", "Application has a marketed brand name; the responsible-party fallback brand rule is not triggered.")

    describes = brand.describes_age_origin_identity_or_characteristics
    if describes is False:
        b.pass_("DS-LABEL-003", "Brand name was not classified as describing age, origin, identity, or other product characteristics.")
    elif describes is True:
        allowed = brand.qualified_with_brand_word is True or (
            brand.accurately_describes_product is True and brand.conveys_erroneous_impression is False
        )
        if allowed:
            b.pass_("DS-LABEL-003", "Brand name describes product characteristics, but the required accuracy/no-misleading or BRAND-word qualification was satisfied.")
        elif brand.accurately_describes_product is False or brand.conveys_erroneous_impression is True:
            b.fail("DS-LABEL-003", "Brand name describes product characteristics and was resolved as inaccurate, misleading, or not properly qualified.")
        else:
            b.unknown(
                "DS-LABEL-003",
                "Brand name appears to describe age, origin, identity, or characteristics, but the product-accuracy/misleading-impression exception was not resolved.",
                hard_failure=True,
            )
    else:
        b.unknown(
            "DS-LABEL-003",
            "OCR text alone did not determine whether the brand name describes age, origin, identity, or other characteristics.",
            hard_failure=False,
        )


def _evaluate_class_type_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    identity = app.identity
    class_type = label.class_type
    label_ct = _clean(class_type.statement.text)
    app_ct = _clean(identity.class_type_designation)

    if label_ct:
        b.pass_("DS-LABEL-010", f"Class/type designation was extracted as {_q(label_ct)}.")
    else:
        b.fail("DS-LABEL-010", "No class/type designation was extracted from the OCR text blocks.")

    if app_ct:
        b.bool_rule(
            "DS-LABEL-011",
            class_type.matches_application_class_type,
            pass_reason=f"Extracted class/type {_q(label_ct)} matches application class/type {_q(app_ct)}.",
            fail_reason=f"Extracted class/type {_q(label_ct or '<missing>')} does not match application class/type {_q(app_ct)}.",
            unknown_reason=f"Application class/type is {_q(app_ct)}, but the OCR/LLM output did not resolve the class/type match.",
            hard_failure=True,
        )
    else:
        b.unknown("DS-LABEL-011", "Application class/type was not available in the copied application detail, so the label/application match could not be checked.", hard_failure=True)

    sufficiency = class_type.class_or_type_name_is_sufficient
    if sufficiency is None:
        sufficiency = identity.class_or_type_name_is_sufficient_designation
    b.bool_rule(
        "DS-LABEL-012",
        sufficiency,
        pass_reason="The extracted type/class name was resolved as sufficient for the product designation.",
        fail_reason="The extracted type/class name was resolved as insufficient for the product designation.",
        unknown_reason="The class/type chart sufficiency of the extracted designation was not resolved.",
        hard_failure=False,
    )
    b.bool_rule(
        "DS-LABEL-013",
        sufficiency,
        pass_reason="The extracted class/type designation was resolved as sufficient under the applicable class/type chart.",
        fail_reason="The extracted class/type designation was resolved as insufficient under the applicable class/type chart.",
        unknown_reason="The class/type chart did not resolve whether this designation is sufficient as stated.",
        hard_failure=False,
    )

    if identity.is_distilled_spirits_specialty:
        b.bool_rule(
            "DS-LABEL-017",
            class_type.specialty_statement_of_composition_present,
            pass_reason="Product is a distilled spirits specialty and the label includes a composition/character statement.",
            fail_reason="Product is a distilled spirits specialty, but no adequate composition/character statement was resolved on the label.",
            unknown_reason="Product is a distilled spirits specialty, but OCR/LLM output did not resolve whether the required statement of composition is present.",
            hard_failure=True,
        )
        b.bool_rule(
            "DS-LABEL-018",
            class_type.specialty_statement_of_composition_present,
            pass_reason="Specialty-product statement of composition was resolved as present.",
            fail_reason="Specialty-product statement of composition was required but not resolved as present.",
            unknown_reason="Specialty-product statement of composition could not be resolved from OCR/LLM output.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-017", "Application does not identify the product as a distilled spirits specialty; rule is not triggered.")
        b.pass_("DS-LABEL-018", "Application facts do not show a product requiring specialty labeling; rule is not triggered.")

    _conditional_bool(
        b,
        "DS-LABEL-019",
        identity.is_imitation,
        class_type.imitation_designation_present,
        triggered_pass="Product is imitation distilled spirits and the imitation designation was resolved as present.",
        triggered_fail="Product is imitation distilled spirits, but the imitation designation was not resolved as present.",
        triggered_unknown="Product is imitation distilled spirits, but OCR/LLM output did not resolve the required imitation designation.",
        not_triggered="Application does not identify the product as imitation distilled spirits; rule is not triggered.",
    )
    _conditional_bool(
        b,
        "DS-LABEL-020",
        identity.is_recognized_cocktail,
        class_type.cocktail_component_declaration_present,
        triggered_pass="Product is a recognized cocktail and the cocktail/component declaration was resolved as present.",
        triggered_fail="Product is a recognized cocktail, but the cocktail/component declaration was not resolved as present.",
        triggered_unknown="Product is a recognized cocktail, but OCR/LLM output did not resolve the required cocktail/component declaration.",
        not_triggered="Application does not identify the product as a recognized cocktail; rule is not triggered.",
    )
    _conditional_bool(
        b,
        "DS-LABEL-021",
        identity.is_flavored,
        class_type.predominant_flavor_declared,
        triggered_pass="Product is flavored and the predominant flavor was resolved as part of the class/type designation.",
        triggered_fail="Product is flavored, but the predominant flavor was not resolved as part of the class/type designation.",
        triggered_unknown="Product is flavored, but OCR/LLM output did not resolve whether the predominant flavor appears in the class/type designation.",
        not_triggered="Application does not identify the product as a flavored distilled spirit; rule is not triggered.",
    )

    wine = identity.wine_addition
    if wine and identity.is_flavored:
        base = _norm(identity.flavored_base_class_type or identity.type_name or identity.class_type_designation)
        percent = wine.percent_by_volume_of_finished_product
        if any(word in base for word in ["gin", "rum", "vodka", "whisky", "whiskey"]):
            if percent is not None and percent <= 2.5:
                b.pass_("DS-LABEL-022", f"Added wine is {percent:g}% of finished product; the >2.5% wine declaration trigger is not met.")
            else:
                b.bool_rule(
                    "DS-LABEL-022",
                    class_type.wine_class_type_and_percent_declared,
                    pass_reason="Wine class/type and percentage were resolved as present in the class/type designation.",
                    fail_reason="Wine class/type and percentage were required but not resolved as present in the class/type designation.",
                    unknown_reason="Wine addition may trigger a wine class/type and percentage declaration, but the required label text was not resolved.",
                    hard_failure=True,
                )
        else:
            b.pass_("DS-LABEL-022", "Product is not flavored gin, rum, vodka, or whisky; rule is not triggered.")

        if "brandy" in base:
            exception = (
                percent is not None
                and percent <= 15
                and wine.percent_of_wine_from_base_commodity is not None
                and wine.percent_of_wine_from_base_commodity >= 12.5
            )
            if exception:
                b.pass_("DS-LABEL-023", "Flavored brandy wine-addition exception was resolved; wine class/type and percentage declaration is not required.")
            else:
                b.bool_rule(
                    "DS-LABEL-023",
                    class_type.wine_class_type_and_percent_declared,
                    pass_reason="Flavored brandy wine class/type and percentage were resolved as present.",
                    fail_reason="Flavored brandy wine class/type and percentage were required but not resolved as present.",
                    unknown_reason="Flavored brandy has wine addition facts, but the required wine class/type and percentage declaration was not resolved.",
                    hard_failure=True,
                )
        else:
            b.pass_("DS-LABEL-023", "Product is not flavored brandy with added wine; rule is not triggered.")
    else:
        b.pass_("DS-LABEL-022", "Application does not identify a wine addition to flavored gin, rum, vodka, or whisky; rule is not triggered.")
        b.pass_("DS-LABEL-023", "Application does not identify a wine addition to flavored brandy; rule is not triggered.")

    _conditional_bool(
        b,
        "DS-LABEL-024",
        identity.is_creme_de,
        class_type.predominant_flavor_declared,
        triggered_pass="Creme de product has the predominant flavor resolved in the designation.",
        triggered_fail="Creme de product did not resolve the predominant flavor in the designation.",
        triggered_unknown="Creme de product requires the predominant flavor in the designation, but OCR/LLM output did not resolve it.",
        not_triggered="Application does not identify a Creme de product; rule is not triggered.",
    )

    # More specialized class/type rules.  These pass when their trigger facts are absent,
    # fail when trigger facts and a negative resolved value are present, and otherwise stay unknown.
    foreign_whisky_trigger = identity.is_whisky and identity.produced_country is not None and not _is_us_country(identity.produced_country)
    _conditional_bool(
        b,
        "DS-LABEL-025",
        foreign_whisky_trigger,
        class_type.foreign_whisky_origin_qualifier_present,
        triggered_pass="Foreign-produced whisky uses the required origin qualifier.",
        triggered_fail="Foreign-produced whisky does not use the required origin qualifier.",
        triggered_unknown="Foreign-produced whisky may require an origin qualifier, but OCR/LLM output did not resolve it.",
        not_triggered="Application does not identify a foreign-produced whisky requiring this qualifier; rule is not triggered.",
        hard_failure=False,
    )

    domestic_imported_components_trigger = bool(identity.domestic_and_imported_whisky_components)
    _conditional_bool(
        b,
        "DS-LABEL-026",
        domestic_imported_components_trigger,
        class_type.domestic_foreign_whisky_percent_origin_declared,
        triggered_pass="Domestic/imported whisky component percentages and origins were resolved as declared.",
        triggered_fail="Domestic/imported whisky component percentages and origins were required but not resolved as declared.",
        triggered_unknown="Domestic/imported whisky components exist, but OCR/LLM output did not resolve percentage/origin declarations.",
        not_triggered="Application does not identify a domestic/imported whisky blend; rule is not triggered.",
    )

    if identity.is_compounded_gin:
        value = None if class_type.compounded_gin_improperly_described_as_distilled is None else not class_type.compounded_gin_improperly_described_as_distilled
        b.bool_rule(
            "DS-LABEL-028",
            value,
            pass_reason="Compounded gin was not resolved as being improperly described as distilled.",
            fail_reason="Compounded gin was resolved as improperly described as distilled.",
            unknown_reason="Product is compounded gin, but OCR/LLM output did not resolve whether it is described as distilled.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-028", "Application does not identify compounded gin; rule is not triggered.")

    brandy_label_text = _norm(label_ct)
    if identity.is_brandy:
        is_plain_brandy_label = brandy_label_text == "brandy"
        is_grape_or_unspecified = identity.brandy_base_fruit is None or _norm(identity.brandy_base_fruit) == "grape"
        if is_plain_brandy_label and not is_grape_or_unspecified:
            b.fail("DS-LABEL-029", "Label uses “Brandy” by itself, but application facts indicate a non-grape brandy.")
        else:
            b.pass_("DS-LABEL-029", "Brandy designation is not contradicted by the application fruit/component facts.")
    else:
        b.pass_("DS-LABEL-029", "Application does not identify a brandy product; rule is not triggered.")

    _conditional_bool(
        b,
        "DS-LABEL-030",
        identity.is_brandy and identity.brandy_base_fruit is not None and _norm(identity.brandy_base_fruit) != "grape",
        class_type.brandy_fruit_or_component_percentages_compliant,
        triggered_pass="Non-grape brandy fruit identification was resolved as compliant.",
        triggered_fail="Non-grape brandy fruit identification was resolved as noncompliant or absent.",
        triggered_unknown="Non-grape brandy requires fruit identification, but OCR/LLM output did not resolve it.",
        not_triggered="Application does not identify a non-grape brandy; rule is not triggered.",
    )
    _conditional_bool(
        b,
        "DS-LABEL-031",
        len(identity.brandy_components) >= 2,
        class_type.brandy_fruit_or_component_percentages_compliant,
        triggered_pass="Blended brandy component percentages/names were resolved as compliant.",
        triggered_fail="Blended brandy component percentages/names were resolved as noncompliant or absent.",
        triggered_unknown="Blended brandy component percentages/names were not resolved from OCR/LLM output.",
        not_triggered="Application does not identify a blend of multiple brandy types; rule is not triggered.",
    )
    _conditional_bool(
        b,
        "DS-LABEL-032",
        len(identity.fruit_brandy_fruits) >= 2,
        class_type.brandy_fruit_or_component_percentages_compliant,
        triggered_pass="Multi-fruit brandy percentages/names were resolved as compliant.",
        triggered_fail="Multi-fruit brandy percentages/names were resolved as noncompliant or absent.",
        triggered_unknown="Multi-fruit brandy percentages/names were not resolved from OCR/LLM output.",
        not_triggered="Application does not identify a fruit brandy derived from two or more fruits; rule is not triggered.",
    )

    sambuca_trigger = identity.uses_sambuca_term and _norm(identity.produced_country) != "italy"
    _conditional_bool(
        b,
        "DS-LABEL-034",
        sambuca_trigger,
        class_type.sambuca_or_goldwasser_origin_qualifier_present,
        triggered_pass="Non-Italian Sambuca origin qualifier was resolved as present.",
        triggered_fail="Non-Italian Sambuca origin qualifier was required but not resolved as present.",
        triggered_unknown="Non-Italian Sambuca origin qualifier requirement was triggered, but OCR/LLM output did not resolve the qualifier.",
        not_triggered="Application does not identify a non-Italian Sambuca use; rule is not triggered.",
    )
    goldwasser_trigger = identity.uses_goldwasser_term and _norm(identity.produced_country) != "germany"
    _conditional_bool(
        b,
        "DS-LABEL-035",
        goldwasser_trigger,
        class_type.sambuca_or_goldwasser_origin_qualifier_present,
        triggered_pass="Non-German Goldwasser origin qualifier was resolved as present.",
        triggered_fail="Non-German Goldwasser origin qualifier was required but not resolved as present.",
        triggered_unknown="Non-German Goldwasser origin qualifier requirement was triggered, but OCR/LLM output did not resolve the qualifier.",
        not_triggered="Application does not identify a non-German Goldwasser use; rule is not triggered.",
    )
    arak_trigger = (
        identity.uses_arak_arack_or_raki_term
        and identity.sugar_dextrose_levulose_percent_by_weight is not None
        and identity.sugar_dextrose_levulose_percent_by_weight < 2.5
    )
    _conditional_bool(
        b,
        "DS-LABEL-036",
        arak_trigger,
        class_type.arak_arack_raki_specialty_composition_statement_present,
        triggered_pass="Arak/Arack/Raki low-sugar specialty statement was resolved as present.",
        triggered_fail="Arak/Arack/Raki low-sugar specialty statement was required but not resolved as present.",
        triggered_unknown="Arak/Arack/Raki low-sugar rule was triggered, but OCR/LLM output did not resolve the specialty statement.",
        not_triggered="Application does not identify a low-sugar Arak/Arack/Raki use; rule is not triggered.",
    )

    if identity.minimum_bottled_abv_for_class_type is not None:
        value = class_type.minimum_abv_for_class_type_satisfied
        if value is None and app.alcohol.abv_percent is not None:
            value = app.alcohol.abv_percent >= identity.minimum_bottled_abv_for_class_type
        b.bool_rule(
            "DS-LABEL-037",
            value,
            pass_reason=f"Known ABV satisfies the class/type minimum of {identity.minimum_bottled_abv_for_class_type:g}% ABV.",
            fail_reason=f"Known ABV does not satisfy the class/type minimum of {identity.minimum_bottled_abv_for_class_type:g}% ABV.",
            unknown_reason="Class/type has a minimum bottled ABV, but the needed ABV comparison was not resolved.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-037", "No minimum bottled ABV requirement was identified for the application class/type.")

    if identity.required_country_or_region_for_class_type:
        value = class_type.required_origin_for_class_type_satisfied
        if value is None and identity.produced_country:
            value = _norm(identity.required_country_or_region_for_class_type) in _norm(identity.produced_country)
        b.bool_rule(
            "DS-LABEL-038",
            value,
            pass_reason=f"Known production origin satisfies required class/type origin {_q(identity.required_country_or_region_for_class_type)}.",
            fail_reason=f"Known production origin does not satisfy required class/type origin {_q(identity.required_country_or_region_for_class_type)}.",
            unknown_reason="Class/type has a required production country/region, but the origin comparison was not resolved.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-038", "No required production country/region was identified for the application class/type.")


def _evaluate_responsible_party_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    statements = label.responsible_party_statements
    imported = app.import_status != ds.ImportStatus.DOMESTIC

    if not imported:
        has_domestic = any(_statement_has_any_role(stmt, DOMESTIC_RESPONSIBLE_ROLES) for stmt in statements)
        b.bool_rule(
            "DS-LABEL-040",
            has_domestic,
            pass_reason="Domestic responsible-party name/address statement was extracted.",
            fail_reason="Domestic product requires a responsible-party name/address statement, but none was extracted.",
            unknown_reason="Domestic responsible-party statement could not be resolved from OCR text.",
            hard_failure=True,
        )
        _evaluate_role_phrase(b, "DS-LABEL-041", statements, DOMESTIC_RESPONSIBLE_ROLES, "domestic")
        _evaluate_responsible_name_match(b, "DS-LABEL-042", review, statements)
        _evaluate_responsible_address_match(b, "DS-LABEL-043", review, statements, "domestic")
        if any(p.uses_principal_place_of_business for p in app.responsible_parties):
            value = any(p.actual_operation_address_marked_on_label_or_container is True for p in app.responsible_parties)
            if any(p.actual_operation_address_marked_on_label_or_container is False for p in app.responsible_parties):
                b.fail("DS-LABEL-044", "Application uses a principal-place-of-business address and indicates no actual-operation address marking.")
            elif value:
                b.pass_("DS-LABEL-044", "Application uses a principal-place-of-business address and actual-operation address marking was resolved as present.")
            else:
                b.unknown("DS-LABEL-044", "Application uses a principal-place-of-business address; OCR text did not resolve whether the actual-operation address is marked elsewhere on the label/container.", hard_failure=True)
        else:
            b.pass_("DS-LABEL-044", "Application does not use a principal-place-of-business address for a domestic responsible party; rule is not triggered.")
    else:
        b.pass_("DS-LABEL-040", "Application is imported; domestic responsible-party rule is not triggered.")
        b.pass_("DS-LABEL-041", "Application is imported; domestic explanatory-phrase rule is not triggered.")
        b.pass_("DS-LABEL-042", "Application is imported; domestic basic-permit name rule is not triggered.")
        b.pass_("DS-LABEL-043", "Application is imported; domestic address rule is not triggered.")
        b.pass_("DS-LABEL-044", "Application is imported; domestic principal-place-of-business marking rule is not triggered.")

    if app.import_status == ds.ImportStatus.IMPORTED_BOTTLED_BEFORE_IMPORTATION:
        has_importer = any(_statement_has_any_role(stmt, IMPORTED_BEFORE_ROLES) for stmt in statements)
        b.bool_rule(
            "DS-LABEL-050",
            has_importer,
            pass_reason="Imported-before-importation importer/sole-agent name/address statement was extracted.",
            fail_reason="Imported-before-importation product requires importer/sole-agent name/address, but none was extracted.",
            unknown_reason="Importer/sole-agent name/address statement could not be resolved from OCR text.",
            hard_failure=True,
        )
        _evaluate_role_phrase(b, "DS-LABEL-051", statements, IMPORTED_BEFORE_ROLES, "imported-before-importation")
        b.pass_("DS-LABEL-052", "Application is not marked as imported after importation; imported-after-importation rule is not triggered.")
        b.pass_("DS-LABEL-053", "Application is not marked as bottled/packed/filled in the U.S. after importation; U.S. bottling phrase rule is not triggered.")
        _evaluate_responsible_address_match(b, "DS-LABEL-054", review, statements, "imported")
    elif app.import_status == ds.ImportStatus.IMPORTED_BOTTLED_AFTER_IMPORTATION:
        b.pass_("DS-LABEL-050", "Application is marked as imported after importation; imported-before-importation rule is not triggered.")
        b.pass_("DS-LABEL-051", "Application is marked as imported after importation; imported-before-importation phrase rule is not triggered.")
        has_relevant = any(_statement_has_any_role(stmt, IMPORTED_AFTER_ROLES) for stmt in statements)
        b.bool_rule(
            "DS-LABEL-052",
            has_relevant,
            pass_reason="Imported-after-importation responsible-party name/address statement was extracted.",
            fail_reason="Imported-after-importation product requires importer and/or bottler/packer/filler name/address, but none was extracted.",
            unknown_reason="Imported-after-importation responsible-party statement could not be resolved from OCR text.",
            hard_failure=True,
        )
        value = any(stmt.us_bottling_packing_or_filling_indicated_for_import is True for stmt in statements)
        if value:
            b.pass_("DS-LABEL-053", "Label phrase indicates U.S. bottling/packing/filling for an imported-after-importation product.")
        elif any(stmt.us_bottling_packing_or_filling_indicated_for_import is False for stmt in statements):
            b.fail("DS-LABEL-053", "Application is treated as imported-after-importation, but the extracted phrase does not indicate U.S. bottling/packing/filling.")
        elif has_relevant:
            b.unknown("DS-LABEL-053", "Application is treated as imported-after-importation, but OCR/LLM output did not resolve whether the phrase indicates U.S. bottling/packing/filling.", hard_failure=True)
        else:
            b.fail("DS-LABEL-053", "No imported-after-importation responsible-party phrase was extracted to indicate U.S. bottling/packing/filling.")
        _evaluate_responsible_address_match(b, "DS-LABEL-054", review, statements, "imported")
    else:
        b.pass_("DS-LABEL-050", "Application is domestic; imported-before-importation rule is not triggered.")
        b.pass_("DS-LABEL-051", "Application is domestic; imported-before-importation phrase rule is not triggered.")
        b.pass_("DS-LABEL-052", "Application is domestic; imported-after-importation rule is not triggered.")
        b.pass_("DS-LABEL-053", "Application is domestic; imported-after-importation U.S. bottling phrase rule is not triggered.")
        b.pass_("DS-LABEL-054", "Application is domestic; imported address rule is not triggered.")


def _evaluate_country_of_origin_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label.country_of_origin
    imported = app.import_status != ds.ImportStatus.DOMESTIC

    if not imported:
        b.pass_("DS-LABEL-060", "Application is domestic; imported country-of-origin statement is not required.")
        b.pass_("DS-LABEL-061", "Application is domestic; imported country-of-origin match rule is not triggered.")
        return

    present = label.statement.is_present
    b.bool_rule(
        "DS-LABEL-060",
        present,
        pass_reason=f"Country-of-origin statement was extracted as {_q(label.statement.text)}.",
        fail_reason="Imported product requires a country-of-origin statement, but none was extracted.",
        unknown_reason="Imported country-of-origin statement could not be resolved from OCR text.",
        hard_failure=True,
    )
    if app.country_of_origin:
        b.bool_rule(
            "DS-LABEL-061",
            label.matches_application_country,
            pass_reason=f"Extracted country of origin matches application origin {_q(app.country_of_origin)}.",
            fail_reason=f"Extracted country of origin {_q(label.country or label.statement.text)} does not match application origin {_q(app.country_of_origin)}.",
            unknown_reason=f"Application origin is {_q(app.country_of_origin)}, but OCR/LLM output did not resolve the country match.",
            hard_failure=True,
        )
    else:
        b.unknown("DS-LABEL-061", "Application country of origin was not available, so the country-of-origin match could not be checked.", hard_failure=True)


def _evaluate_net_contents_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label.net_contents
    net_ml = label.net_contents_ml

    if net_ml is not None:
        b.pass_("DS-LABEL-070", f"Net contents were extracted as {net_ml} mL.")
    else:
        b.fail("DS-LABEL-070", "No parseable net-contents statement was extracted from the OCR text blocks.")

    if app.net_contents.net_contents_ml is not None:
        b.bool_rule(
            "DS-LABEL-071",
            label.matches_application_net_contents,
            pass_reason=f"Extracted net contents {net_ml} mL match application net contents {app.net_contents.net_contents_ml} mL.",
            fail_reason=f"Extracted net contents {_ml(net_ml)} do not match application net contents {_ml(app.net_contents.net_contents_ml)}.",
            unknown_reason="Application and label net contents exist, but their match was not resolved.",
            hard_failure=True,
        )
    else:
        b.unknown("DS-LABEL-071", "Copied application detail did not include total bottle capacity, so label/application net-contents matching could not be checked.", hard_failure=False)

    b.bool_rule(
        "DS-LABEL-072",
        label.is_metric_standard_of_fill,
        pass_reason=f"Extracted net contents {_ml(net_ml)} are a permitted metric standard of fill for the inferred container type.",
        fail_reason=f"Extracted net contents {_ml(net_ml)} are not a permitted metric standard of fill for the inferred container type.",
        unknown_reason="Net contents or container type were not resolved enough to check standard of fill.",
        hard_failure=True,
    )

    if app.net_contents.container_kind == ds.ContainerKind.CAN:
        b.pass_("DS-LABEL-073", "Container is marked as a can, so the non-can standards-of-fill list is not triggered.")
        b.bool_rule(
            "DS-LABEL-074",
            net_ml in ds.CAN_STANDARD_FILLS_ML if net_ml is not None else None,
            pass_reason=f"Can net contents {_ml(net_ml)} are in the permitted can standards-of-fill list.",
            fail_reason=f"Can net contents {_ml(net_ml)} are not in the permitted can standards-of-fill list.",
            unknown_reason="Can container type is known, but net contents were not parseable for the can standards-of-fill check.",
            hard_failure=True,
        )
    else:
        b.bool_rule(
            "DS-LABEL-073",
            net_ml in ds.NON_CAN_STANDARD_FILLS_ML if net_ml is not None else None,
            pass_reason=f"Non-can net contents {_ml(net_ml)} are in the permitted non-can standards-of-fill list.",
            fail_reason=f"Non-can net contents {_ml(net_ml)} are not in the permitted non-can standards-of-fill list.",
            unknown_reason="Non-can container type is inferred, but net contents were not parseable for the standards-of-fill check.",
            hard_failure=True,
        )
        b.pass_("DS-LABEL-074", "Container is not marked as a can, so the can standards-of-fill list is not triggered.")


def _evaluate_alcohol_content_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label.alcohol_content
    abv = label.abv_percent

    if abv is not None:
        b.pass_("DS-LABEL-080", f"Alcohol content was extracted as {abv:g}% ABV.")
    else:
        b.fail("DS-LABEL-080", "No parseable alcohol-content/ABV statement was extracted from the OCR text blocks.")

    b.bool_rule(
        "DS-LABEL-081",
        label.has_percent_alcohol_by_volume_phrase,
        pass_reason=f"Alcohol-content statement uses an accepted percent-alcohol-by-volume form: {_q(label.statement.text)}.",
        fail_reason=f"Alcohol-content statement was extracted but does not use an accepted percent-alcohol-by-volume form: {_q(label.statement.text)}.",
        unknown_reason="OCR text did not resolve whether the alcohol-content statement uses percent alcohol by volume.",
        hard_failure=True,
    )

    if app.alcohol.contains_solid_material:
        b.bool_rule(
            "DS-LABEL-082",
            label.uses_bottled_at_phrase_for_products_with_solids,
            pass_reason="Application indicates solid material and the ABV statement uses the required BOTTLED AT form.",
            fail_reason="Application indicates solid material, but the ABV statement does not use the required BOTTLED AT form.",
            unknown_reason="Application indicates solid material, but OCR/LLM output did not resolve the required BOTTLED AT ABV form.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-082", "Application does not indicate solid material; BOTTLED AT ABV wording is not required.")

    if app.alcohol.abv_percent is not None:
        b.bool_rule(
            "DS-LABEL-083",
            label.matches_application_abv_with_tolerance,
            pass_reason=f"Extracted ABV {abv:g}% matches application ABV {app.alcohol.abv_percent:g}% within the applicable tolerance.",
            fail_reason=f"Extracted ABV {_pct(abv)} does not match application ABV {_pct(app.alcohol.abv_percent)} within the applicable tolerance.",
            unknown_reason="Application and label ABV exist, but the tolerance comparison was not resolved.",
            hard_failure=True,
        )
    else:
        b.unknown("DS-LABEL-083", "Copied application detail did not expose application ABV, so label/application ABV matching could not be checked.", hard_failure=False)

    tolerance_value = _abv_tolerance_result(app, label)
    # The following rules are mutually exclusive tolerance branches.  Non-applicable branches pass.
    if app.alcohol.solids_mg_per_100ml is not None and app.alcohol.solids_mg_per_100ml > 600:
        _tolerance_rule(b, "DS-LABEL-084", tolerance_value, "spirits with solids over 600 mg/100 mL", 0.25, hard_failure=app.alcohol.abv_percent is not None)
        b.pass_("DS-LABEL-085", "The solids-over-600 mg/100 mL tolerance branch applies, so the 50/100 mL branch is not triggered.")
        b.pass_("DS-LABEL-086", "The solids-over-600 mg/100 mL tolerance branch applies, so the general 0.15% branch is not triggered.")
    elif app.net_contents.net_contents_ml in {50, 100} or review.label.net_contents.net_contents_ml in {50, 100}:
        b.pass_("DS-LABEL-084", "The 50/100 mL tolerance branch applies, so the solids-over-600 mg/100 mL branch is not triggered.")
        _tolerance_rule(b, "DS-LABEL-085", tolerance_value, "50 mL or 100 mL container", 0.25, hard_failure=app.alcohol.abv_percent is not None)
        b.pass_("DS-LABEL-086", "The 50/100 mL tolerance branch applies, so the general 0.15% branch is not triggered.")
    else:
        b.pass_("DS-LABEL-084", "No solids-over-600 mg/100 mL trigger was identified.")
        b.pass_("DS-LABEL-085", "Container is not identified as 50 mL or 100 mL.")
        _tolerance_rule(b, "DS-LABEL-086", tolerance_value, "all-other-spirits", 0.15, hard_failure=app.alcohol.abv_percent is not None)

    if label.proof is None:
        b.pass_("DS-LABEL-088", "Proof is not shown, so proof-distinguishing punctuation/format rule is not triggered.")
    else:
        b.bool_rule(
            "DS-LABEL-088",
            label.proof_is_distinguished_from_abv_statement,
            pass_reason=f"Proof value {label.proof:g} is set off or otherwise distinguished from the ABV statement.",
            fail_reason=f"Proof value {label.proof:g} is shown but was not resolved as distinguished from the ABV statement.",
            unknown_reason=f"Proof value {label.proof:g} is shown, but OCR text did not resolve whether it is distinguished from the ABV statement.",
            hard_failure=True,
        )


def _evaluate_disclosure_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    disclosures = app.disclosures

    if disclosures.coloring_material_changes_class_type is True:
        b.bool_rule(
            "DS-LABEL-106",
            label.coloring_disclosure.class_type_reflects_materials_when_materials_change_class_type,
            pass_reason="Coloring/flavoring/blending materials change class/type and the resulting designation was resolved as correct.",
            fail_reason="Coloring/flavoring/blending materials change class/type, but the resulting designation was not resolved as correct.",
            unknown_reason="Coloring/flavoring/blending materials may change class/type, but OCR/LLM output did not resolve the resulting designation.",
            hard_failure=True,
        )
    elif disclosures.coloring_material_changes_class_type is False or not disclosures.contains_coloring_materials:
        b.pass_("DS-LABEL-106", "Application does not indicate coloring/flavoring/blending materials that change class/type; rule is not triggered.")
    else:
        b.unknown("DS-LABEL-106", "Application facts do not resolve whether coloring/flavoring/blending materials change class/type.", hard_failure=False)

    wood_trigger = disclosures.treated_with_wood_other_than_oak_container_contact and disclosures.wood_treatment_exception_applies is not True
    if wood_trigger:
        b.bool_rule(
            "DS-LABEL-110",
            label.wood_treatment_disclosure.contains_colored_and_flavored_with_wood_phrase,
            pass_reason="Wood-treatment disclosure contains the required COLORED AND FLAVORED WITH WOOD phrase.",
            fail_reason="Wood-treatment disclosure is required but the required COLORED AND FLAVORED WITH WOOD phrase was not resolved as present.",
            unknown_reason="Wood treatment triggers disclosure, but OCR/LLM output did not resolve the required phrase.",
            hard_failure=True,
        )
        is_whisky_or_brandy = app.identity.is_whisky or app.identity.is_brandy
        b.bool_rule(
            "DS-LABEL-111",
            is_whisky_or_brandy,
            pass_reason="Wood-treatment trigger applies to a whisky or brandy product.",
            fail_reason="Wood-treatment trigger was set, but application identity is not whisky or brandy.",
            unknown_reason="Wood-treatment trigger was set, but product class was not resolved as whisky or brandy.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-110", "Application does not indicate non-exempt whisky/brandy treatment with wood outside oak-container contact; disclosure is not required.")
        b.pass_("DS-LABEL-111", "Wood-treatment disclosure scope is not triggered by the application facts.")

    _conditional_bool(
        b,
        "DS-LABEL-120",
        disclosures.contains_fdc_yellow_5,
        label.fdc_yellow_5_disclosure.contains_required_phrase,
        triggered_pass="Application indicates FD&C Yellow #5 and the required disclosure phrase was resolved as present.",
        triggered_fail="Application indicates FD&C Yellow #5, but the required disclosure phrase was not resolved as present.",
        triggered_unknown="Application indicates FD&C Yellow #5, but OCR/LLM output did not resolve the required disclosure phrase.",
        not_triggered="Application does not indicate FD&C Yellow #5; disclosure is not required.",
    )
    _conditional_bool(
        b,
        "DS-LABEL-130",
        disclosures.contains_saccharin,
        label.saccharin_disclosure.exact_required_text_present,
        triggered_pass="Application indicates saccharin and the exact required saccharin disclosure was resolved as present.",
        triggered_fail="Application indicates saccharin, but the exact required saccharin disclosure was not resolved as present.",
        triggered_unknown="Application indicates saccharin, but OCR/LLM output did not resolve the exact required saccharin disclosure.",
        not_triggered="Application does not indicate saccharin; disclosure is not required.",
    )

    sulfite_required = disclosures.contains_sulfites_at_declaration_threshold
    if sulfite_required is True:
        has_sulfite_disclosure = any(
            value is True
            for value in [
                label.sulfite_declaration.contains_sulfites_phrase_present,
                label.sulfite_declaration.contains_sulfiting_agents_phrase_present,
                label.sulfite_declaration.specific_sulfiting_agents_declared,
            ]
        )
        b.bool_rule(
            "DS-LABEL-140",
            has_sulfite_disclosure,
            pass_reason="Application indicates sulfites at/above 10 ppm and an accepted sulfite declaration was resolved as present.",
            fail_reason="Application indicates sulfites at/above 10 ppm, but no accepted sulfite declaration was resolved as present.",
            unknown_reason="Application indicates sulfites at/above 10 ppm, but OCR/LLM output did not resolve an accepted sulfite declaration.",
            hard_failure=True,
        )
    elif sulfite_required is False:
        b.pass_("DS-LABEL-140", "Application indicates sulfur dioxide is below 10 ppm; sulfite declaration is not required.")
    else:
        b.unknown("DS-LABEL-140", "Application detail did not include sulfur dioxide ppm, so sulfite-declaration applicability could not be determined.", hard_failure=False)


def _evaluate_commodity_statement_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label.commodity_statement
    group = app.commodity_statement.group

    if group == ds.CommodityStatementGroup.GROUP_1_PERCENT_AND_COMMODITY:
        b.bool_rule(
            "DS-LABEL-150",
            label.group1_percent_and_commodity_present,
            pass_reason="Application is commodity-statement Group 1 and percentage/commodity statement was resolved as present.",
            fail_reason="Application is commodity-statement Group 1, but percentage/commodity statement was not resolved as present.",
            unknown_reason="Application is commodity-statement Group 1, but OCR/LLM output did not resolve the percentage/commodity statement.",
            hard_failure=True,
        )
        b.pass_("DS-LABEL-151", "Application commodity-statement group is Group 1.")
        b.bool_rule(
            "DS-LABEL-152",
            label.group1_percent_and_commodity_present,
            pass_reason="Group 1 commodity statement uses a percentage-plus-commodity form.",
            fail_reason="Group 1 commodity statement was not resolved in a percentage-plus-commodity form.",
            unknown_reason="Group 1 commodity statement format was not resolved from OCR/LLM output.",
            hard_failure=True,
        )
        b.pass_("DS-LABEL-153", "Application is Group 1, so Group 2 commodity-statement rule is not triggered.")
        b.pass_("DS-LABEL-154", "Application is Group 1, so Group 2 commodity-statement membership rule is not triggered.")
        b.pass_("DS-LABEL-155", "Application is Group 1, so Group 2 DISTILLED FROM form rule is not triggered.")
    elif group == ds.CommodityStatementGroup.GROUP_2_COMMODITY_ONLY:
        b.pass_("DS-LABEL-150", "Application is Group 2, so Group 1 commodity-statement rule is not triggered.")
        b.pass_("DS-LABEL-151", "Application is Group 2, so Group 1 membership rule is not triggered.")
        b.pass_("DS-LABEL-152", "Application is Group 2, so Group 1 percentage-plus-commodity form rule is not triggered.")
        b.bool_rule(
            "DS-LABEL-153",
            label.group2_distilled_from_commodity_present,
            pass_reason="Application is commodity-statement Group 2 and commodity statement was resolved as present.",
            fail_reason="Application is commodity-statement Group 2, but commodity statement was not resolved as present.",
            unknown_reason="Application is commodity-statement Group 2, but OCR/LLM output did not resolve the commodity statement.",
            hard_failure=True,
        )
        b.pass_("DS-LABEL-154", "Application commodity-statement group is Group 2.")
        b.bool_rule(
            "DS-LABEL-155",
            label.group2_distilled_from_commodity_present,
            pass_reason="Group 2 commodity statement uses a DISTILLED FROM commodity form.",
            fail_reason="Group 2 commodity statement was not resolved in a DISTILLED FROM commodity form.",
            unknown_reason="Group 2 commodity statement format was not resolved from OCR/LLM output.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-150", "Application is not in commodity-statement Group 1; rule is not triggered.")
        b.pass_("DS-LABEL-151", "Application is not in commodity-statement Group 1; membership rule is not triggered.")
        b.pass_("DS-LABEL-152", "Application is not in commodity-statement Group 1; format rule is not triggered.")
        b.pass_("DS-LABEL-153", "Application is not in commodity-statement Group 2; rule is not triggered.")
        b.pass_("DS-LABEL-154", "Application is not in commodity-statement Group 2; membership rule is not triggered.")
        b.pass_("DS-LABEL-155", "Application is not in commodity-statement Group 2; format rule is not triggered.")


def _evaluate_age_statement_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    age_app = app.age
    age_label = label.age_statement
    age_months = age_app.youngest_component_age_months if age_app.youngest_component_age_months is not None else age_app.actual_age_months

    whisky_age_required = None
    if age_app.is_any_whisky_type:
        if age_months is None:
            whisky_age_required = None
        else:
            whisky_age_required = age_months < 48
    else:
        whisky_age_required = False
    _age_required_rule(
        b,
        "DS-LABEL-160",
        whisky_age_required,
        age_label.required_age_statement_present or age_label.statement.is_present,
        true_reason="Whisky is aged less than 4 years",
        false_reason="Product is not whisky aged less than 4 years",
        unknown_reason="Product is whisky but actual/youngest component age was not available to determine whether age statement is required.",
    )

    grape_lees_required = None
    if age_app.is_grape_lees_brandy:
        grape_lees_required = None if age_months is None else age_months < 24
    else:
        grape_lees_required = False
    _age_required_rule(
        b,
        "DS-LABEL-161",
        grape_lees_required,
        age_label.required_age_statement_present or age_label.statement.is_present,
        true_reason="Grape lees brandy is aged less than 2 years",
        false_reason="Product is not grape lees brandy aged less than 2 years",
        unknown_reason="Product is grape lees brandy but age was not available to determine whether age statement is required.",
    )

    pomace_required = None
    if age_app.is_grape_pomace_or_marc_brandy:
        pomace_required = None if age_months is None else age_months < 24
    else:
        pomace_required = False
    _age_required_rule(
        b,
        "DS-LABEL-162",
        pomace_required,
        age_label.required_age_statement_present or age_label.statement.is_present,
        true_reason="Grape pomace/marc brandy is aged less than 2 years",
        false_reason="Product is not grape pomace/marc brandy aged less than 2 years",
        unknown_reason="Product is grape pomace/marc brandy but age was not available to determine whether age statement is required.",
    )

    misc_age_ref = _coalesce_bool(label.has_misc_age_reference_or_representation, age_app.label_has_misc_age_reference_or_representation)
    _age_required_rule(
        b,
        "DS-LABEL-163",
        misc_age_ref,
        age_label.required_age_statement_present or age_label.statement.is_present,
        true_reason="Label includes a miscellaneous age reference/representation",
        false_reason="No miscellaneous age reference/representation was resolved on the label",
        unknown_reason="OCR/LLM output did not resolve whether the label has a miscellaneous age reference/representation.",
        hard_failure=False,
    )

    distillation_date = _coalesce_bool(label.has_distillation_date, age_app.label_has_distillation_date)
    _age_required_rule(
        b,
        "DS-LABEL-164",
        distillation_date,
        age_label.required_age_statement_present or age_label.statement.is_present,
        true_reason="Label includes a distillation date",
        false_reason="No distillation date was resolved on the label",
        unknown_reason="OCR/LLM output did not resolve whether the label has a distillation date.",
        hard_failure=False,
    )

    any_age_required = any(v is True for v in [whisky_age_required, grape_lees_required, pomace_required, misc_age_ref, distillation_date])
    if any_age_required:
        b.bool_rule(
            "DS-LABEL-166",
            age_label.uses_years_old_or_aged_years_format,
            pass_reason="Required age statement uses the resolved YEARS OLD or AGED YEARS format.",
            fail_reason="Required age statement does not use the resolved YEARS OLD or AGED YEARS format.",
            unknown_reason="Age statement is required, but the YEARS OLD / AGED YEARS format was not resolved.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-166", "No age statement trigger was resolved; standard age-statement format rule is not triggered.")

    _conditional_bool(
        b,
        "DS-LABEL-168",
        age_app.us_whisky_stored_in_reused_oak_containers,
        age_label.uses_reused_cooperage_format,
        triggered_pass="U.S. whisky stored in reused cooperage uses the required reused-cooperage age/storage format.",
        triggered_fail="U.S. whisky stored in reused cooperage does not use the required reused-cooperage age/storage format.",
        triggered_unknown="U.S. whisky stored in reused cooperage requires a specific age/storage format, but OCR/LLM output did not resolve it.",
        not_triggered="Application does not identify U.S. whisky stored in reused cooperage; rule is not triggered.",
    )
    _conditional_bool(
        b,
        "DS-LABEL-169",
        age_app.whisky_contains_neutral_spirits,
        age_label.whisky_neutral_spirits_age_and_percent_statement_present,
        triggered_pass="Whisky with neutral spirits has the required age-and-percentage statement resolved as present.",
        triggered_fail="Whisky with neutral spirits lacks the required age-and-percentage statement.",
        triggered_unknown="Whisky with neutral spirits requires age-and-percentage statement, but OCR/LLM output did not resolve it.",
        not_triggered="Application does not identify whisky containing neutral spirits; rule is not triggered.",
    )
    _conditional_bool(
        b,
        "DS-LABEL-171",
        age_app.whisky_contains_neutral_spirits,
        age_label.percentages_total_100_when_required,
        triggered_pass="Whisky/neutral-spirit percentages were resolved as totaling 100%.",
        triggered_fail="Whisky/neutral-spirit percentages were resolved as not totaling 100%.",
        triggered_unknown="Whisky with neutral spirits requires percentages totaling 100%, but OCR/LLM output did not resolve them.",
        not_triggered="Application does not identify whisky containing neutral spirits; rule is not triggered.",
    )

    age_statement_or_trigger = age_label.statement.is_present or any_age_required
    if age_statement_or_trigger:
        b.bool_rule(
            "DS-LABEL-172",
            age_label.age_is_not_overstated,
            pass_reason="Age statement/reference was resolved as not overstating the product age.",
            fail_reason="Age statement/reference was resolved as overstating the product age.",
            unknown_reason="Age statement/reference exists or is required, but overstatement could not be checked from available application/OCR facts.",
            hard_failure=True,
        )
    else:
        b.pass_("DS-LABEL-172", "No age statement/reference trigger was resolved; age-overstatement rule is not triggered.")


def _evaluate_state_of_distillation_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    state_app = app.state_of_distillation
    state_label = label.state_of_distillation

    if state_app.state_of_distillation_statement_required is True:
        b.bool_rule(
            "DS-LABEL-180",
            state_label.statement.is_present,
            pass_reason=f"State-of-distillation statement was extracted as {_q(state_label.statement.text)}.",
            fail_reason="Application requires a state-of-distillation statement, but none was extracted.",
            unknown_reason="Application requires a state-of-distillation statement, but OCR text did not resolve it.",
            hard_failure=True,
        )
    elif state_app.state_of_distillation_statement_required is False:
        b.pass_("DS-LABEL-180", "Application indicates state-of-distillation statement is not required.")
    elif state_app.is_covered_us_whisky_type:
        b.unknown("DS-LABEL-180", "Product is a covered U.S. whisky type, but application facts did not resolve whether state-of-distillation disclosure is required.", hard_failure=False)
    else:
        b.pass_("DS-LABEL-180", "Application does not identify a covered U.S.-produced whisky type requiring state-of-distillation review.")

    if state_app.is_covered_us_whisky_type:
        b.pass_("DS-LABEL-181", f"Application identifies a covered U.S. whisky type: {_q(state_app.whisky_type)}.")
    elif state_app.produced_in_united_states and state_app.whisky_type:
        b.pass_("DS-LABEL-181", f"Application whisky type {_q(state_app.whisky_type)} is not in the covered state-of-distillation list.")
    else:
        b.pass_("DS-LABEL-181", "Application does not identify U.S.-produced whisky; covered-type list is not triggered.")

    misleading = _coalesce_bool(label.label_may_mislead_about_state_of_distillation, state_app.label_may_mislead_about_state)
    if not state_app.is_covered_us_whisky_type and state_app.state_of_distillation_statement_required is not True:
        b.pass_("DS-LABEL-183", "Application does not identify a covered U.S.-produced whisky type; misleading-state disclosure rule is not triggered.")
    elif misleading is True:
        b.bool_rule(
            "DS-LABEL-183",
            state_label.statement.is_present,
            pass_reason="Label may mislead about state of distillation and a state/dispel statement was extracted.",
            fail_reason="Label may mislead about state of distillation, but no state/dispel statement was extracted.",
            unknown_reason="Label may mislead about state of distillation, but OCR/LLM output did not resolve a state/dispel statement.",
            hard_failure=True,
        )
    elif misleading is False:
        b.pass_("DS-LABEL-183", "Label was resolved as not misleading/deceptive about state of distillation.")
    else:
        b.unknown("DS-LABEL-183", "OCR/LLM output did not resolve whether the label may mislead about state of distillation.", hard_failure=False)


def _evaluate_government_warning_rules(b: _RuleDictBuilder, review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    warning = label.government_warning
    required = _government_warning_required(app, label)

    if required is False:
        b.pass_("DS-LABEL-190", "Government warning is not required because sale/use/ABV/bottling-date conditions are not met.")
        b.pass_("DS-LABEL-191", "Government warning is not required; exact warning text rule is not triggered.")
        b.pass_("DS-LABEL-192", "Government warning is not required; header capitalization/bold rule is not triggered.")
        b.pass_("DS-LABEL-193", "Government warning is not required; body boldness rule is not triggered.")
        b.pass_("DS-LABEL-194", "Government warning is not required; continuous-paragraph rule is not triggered.")
        return
    if required is None:
        b.unknown("DS-LABEL-190", "Government-warning applicability could not be determined because ABV was unavailable from both application and label facts.", hard_failure=True)
        b.unknown("DS-LABEL-191", "Government-warning exact text cannot be evaluated until applicability is resolved.", hard_failure=True)
        b.unknown("DS-LABEL-192", "Government-warning header capitalization/boldness cannot be evaluated until applicability is resolved.", hard_failure=True)
        b.unknown("DS-LABEL-193", "Government-warning body boldness cannot be evaluated until applicability is resolved.", hard_failure=True)
        b.unknown("DS-LABEL-194", "Government-warning paragraph format cannot be evaluated until applicability is resolved.", hard_failure=True)
        return

    warning_present = warning.full_text.is_present or warning.header_text.is_present
    b.bool_rule(
        "DS-LABEL-190",
        warning_present,
        pass_reason="Government warning text/header was extracted from the OCR text blocks.",
        fail_reason="Government warning is required, but no government warning text/header was extracted.",
        unknown_reason="Government warning is required, but OCR text did not resolve whether it is present.",
        hard_failure=True,
    )
    b.bool_rule(
        "DS-LABEL-191",
        warning.exact_required_text_present,
        pass_reason="Government warning contains the exact required text.",
        fail_reason="Missing government warning",
        unknown_reason="OCR/LLM output did not resolve whether the government warning text is exact.",
        hard_failure=True,
    )

    b.bool_rule(
        "DS-LABEL-192",
        warning.header_is_exact_all_caps,
        pass_reason="Government warning header is precisely 'GOVERNMENT WARNING:'.",
        fail_reason="Government warning header is missing or not precisely 'GOVERNMENT WARNING:'.",
        unknown_reason="OCR/LLM output did not resolve whether the government warning header is exact.",
        hard_failure=True,
    )

    b.bool_rule(
        "DS-LABEL-193",
        warning.body_is_not_bold,
        pass_reason="Government warning body was resolved as not bold.",
        fail_reason="Government warning body was resolved as bold, which is not allowed.",
        unknown_reason="OCR text blocks do not prove whether the government warning body is non-bold.",
        hard_failure=False,
    )
    b.bool_rule(
        "DS-LABEL-194",
        warning.appears_as_continuous_paragraph,
        pass_reason="Government warning appears as a continuous paragraph in the OCR text.",
        fail_reason="Government warning was resolved as not appearing as a continuous paragraph.",
        unknown_reason="OCR/LLM output did not resolve whether the government warning appears as a continuous paragraph.",
        hard_failure=False,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _conditional_bool(
    b: _RuleDictBuilder,
    rule_id: str,
    trigger: bool,
    value: bool | None,
    *,
    triggered_pass: str,
    triggered_fail: str,
    triggered_unknown: str,
    not_triggered: str,
    hard_failure: bool = True,
) -> None:
    if trigger:
        b.bool_rule(
            rule_id,
            value,
            pass_reason=triggered_pass,
            fail_reason=triggered_fail,
            unknown_reason=triggered_unknown,
            hard_failure=hard_failure,
        )
    else:
        b.pass_(rule_id, not_triggered)


def _age_required_rule(
    b: _RuleDictBuilder,
    rule_id: str,
    required: bool | None,
    statement_present: bool | None,
    *,
    true_reason: str,
    false_reason: str,
    unknown_reason: str,
    hard_failure: bool = True,
) -> None:
    if required is True:
        b.bool_rule(
            rule_id,
            bool(statement_present),
            pass_reason=f"{true_reason}, and an age statement was resolved as present.",
            fail_reason=f"{true_reason}, but no age statement was resolved as present.",
            unknown_reason=f"{true_reason}, but age-statement presence was not resolved.",
            hard_failure=True,
        )
    elif required is False:
        b.pass_(rule_id, f"{false_reason}; age statement is not required by this rule.")
    else:
        b.unknown(rule_id, unknown_reason, hard_failure=hard_failure)


def _tolerance_rule(b: _RuleDictBuilder, rule_id: str, value: bool | None, branch_name: str, tolerance: float, *, hard_failure: bool = True) -> None:
    b.bool_rule(
        rule_id,
        value,
        pass_reason=f"ABV difference is within {tolerance:g} percentage points for the {branch_name} tolerance branch.",
        fail_reason=f"ABV difference exceeds {tolerance:g} percentage points for the {branch_name} tolerance branch.",
        unknown_reason=f"The {branch_name} tolerance branch applies, but application/label ABV data were insufficient to compare.",
        hard_failure=hard_failure,
    )


def _abv_tolerance_result(app: ds.DistilledSpiritsApplication, label: ds.AlcoholContentLabel) -> bool | None:
    if app.alcohol.abv_percent is None or label.abv_percent is None:
        return None
    tolerance = app.alcohol.allowed_abv_tolerance_percent(app.net_contents.net_contents_ml)
    if tolerance is None:
        return None
    return abs(label.abv_percent - app.alcohol.abv_percent) <= tolerance


def _evaluate_role_phrase(
    b: _RuleDictBuilder,
    rule_id: str,
    statements: list[ds.ResponsiblePartyLabelStatement],
    allowed_roles: frozenset[ds.ResponsiblePartyRole],
    context: str,
) -> None:
    relevant = [stmt for stmt in statements if _statement_has_any_role(stmt, allowed_roles)]
    if not relevant:
        b.fail(rule_id, f"No {context} responsible-party statement with an appropriate explanatory phrase was extracted.")
        return
    if any(stmt.phrase_is_appropriate is True for stmt in relevant):
        phrase = next((stmt.role_phrase for stmt in relevant if stmt.phrase_is_appropriate is True), None)
        b.pass_(rule_id, f"Extracted {context} responsible-party phrase is appropriate: {_q(phrase)}.")
    elif any(stmt.phrase_is_appropriate is False for stmt in relevant):
        phrase = next((stmt.role_phrase for stmt in relevant if stmt.phrase_is_appropriate is False), None)
        b.fail(rule_id, f"Extracted {context} responsible-party phrase was resolved as inappropriate: {_q(phrase)}.")
    else:
        b.unknown(rule_id, f"A {context} responsible-party statement was extracted, but phrase appropriateness was not resolved.", hard_failure=True)


def _evaluate_responsible_name_match(
    b: _RuleDictBuilder,
    rule_id: str,
    review: ds.DistilledSpiritsLabelReviewInput,
    statements: list[ds.ResponsiblePartyLabelStatement],
) -> None:
    parties = review.application.responsible_parties
    if not parties:
        b.unknown(rule_id, "Application responsible-party/basic-permit names were not available for comparison.", hard_failure=True)
        return
    if not statements:
        b.fail(rule_id, "No responsible-party statement was extracted, so basic-permit/application name could not be matched.")
        return
    if any(stmt.name_matches_basic_permit_or_application is True for stmt in statements):
        matched = next((stmt.name for stmt in statements if stmt.name_matches_basic_permit_or_application is True), None)
        b.pass_(rule_id, f"Responsible-party name matches application/basic permit: {_q(matched)}.")
    elif any(stmt.name_matches_basic_permit_or_application is False for stmt in statements):
        found = ", ".join(_q(stmt.name) for stmt in statements if stmt.name)
        expected = ", ".join(_q(p.name) for p in parties)
        b.fail(rule_id, f"Extracted responsible-party name(s) {found or '<none>'} do not match application/basic permit name(s) {expected}.")
    else:
        b.unknown(rule_id, "Responsible-party names were extracted, but the match to application/basic permit was not resolved.", hard_failure=True)


def _evaluate_responsible_address_match(
    b: _RuleDictBuilder,
    rule_id: str,
    review: ds.DistilledSpiritsLabelReviewInput,
    statements: list[ds.ResponsiblePartyLabelStatement],
    context: str,
) -> None:
    parties = review.application.responsible_parties
    if not parties:
        b.unknown(rule_id, f"Application {context} responsible-party address was not available for comparison.", hard_failure=True)
        return
    if not statements:
        b.fail(rule_id, f"No {context} responsible-party statement was extracted, so address could not be matched.")
        return
    for stmt in statements:
        for party in parties:
            if _statement_contains_party_city_state(stmt, party):
                city_state = _city_state(party.address)
                b.pass_(rule_id, f"Extracted responsible-party statement contains required city/state address {city_state}.")
                return
    # Respect an explicit model/vision address match if it was supplied.
    if any(stmt.address_matches_basic_permit_or_application is True for stmt in statements):
        b.pass_(rule_id, f"Responsible-party address was resolved as matching the application/basic permit for {context} product.")
    elif any(stmt.address_matches_basic_permit_or_application is False for stmt in statements):
        b.fail(rule_id, f"Responsible-party address was resolved as not matching the application/basic permit for {context} product.")
    else:
        expected = "; ".join(_city_state(p.address) for p in parties if p.address)
        b.unknown(rule_id, f"Could not confirm required city/state address from OCR text. Expected one of: {expected or '<unavailable>'}.", hard_failure=True)


def _statement_has_any_role(stmt: ds.ResponsiblePartyLabelStatement, roles: frozenset[ds.ResponsiblePartyRole]) -> bool:
    return bool(set(stmt.roles) & set(roles))


def _statement_contains_party_city_state(stmt: ds.ResponsiblePartyLabelStatement, party: ds.ResponsiblePartyApplication) -> bool:
    text = _norm(stmt.statement.text)
    city = _norm(party.address.city)
    state = _norm(party.address.state_or_province)
    if city and state:
        return city in text and state in text
    if city:
        return city in text
    return False


def _government_warning_required(app: ds.DistilledSpiritsApplication, label: ds.DistilledSpiritsLabelExtraction) -> bool | None:
    if not app.sale.for_sale_or_distribution_in_us:
        return False
    if not app.sale.intended_for_human_consumption:
        return False
    if not app.sale.bottled_on_or_after_1989_11_18:
        return False
    abv = app.alcohol.abv_percent if app.alcohol.abv_percent is not None else label.alcohol_content.abv_percent
    if abv is None:
        return None
    return abv >= 0.5


def _coalesce_bool(*values: bool | None) -> bool | None:
    for value in values:
        if value is not None:
            return value
    return None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(str(value).split()).strip()
    return value or None


def _norm(value: str | None) -> str:
    return " ".join(str(value or "").casefold().replace(".", " ").replace(",", " ").split())


def _is_us_country(country: str | None) -> bool:
    return _norm(country) in US_COUNTRY_NAMES


def _q(value: Any) -> str:
    if value is None or value == "":
        return "<missing>"
    return f"'{value}'"


def _ml(value: int | None) -> str:
    return "<missing>" if value is None else f"{value} mL"


def _pct(value: float | None) -> str:
    return "<missing>" if value is None else f"{value:g}%"


def _city_state(address: ds.Address | None) -> str:
    if address is None:
        return "<missing address>"
    parts = [part for part in [address.city, address.state_or_province] if part]
    return ", ".join(parts) if parts else "<missing city/state>"
