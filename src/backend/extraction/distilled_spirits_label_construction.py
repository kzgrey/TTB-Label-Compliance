"""
LLM-assisted construction for distilled-spirits label review inputs.

This module turns two unstructured inputs into the dataclasses defined in
`distilled_spirits_label_dataclasses.py`:

1. copy/pasted COLA/application detail text from the TTB system
2. OCR text blocks from the label image

The LLM is intentionally injected through a small protocol so this code can run with
any JSON-capable model provider.  Without an LLM, the deterministic parser still
populates the fields it can prove from regular expressions and the application paste.

The construction layer is not the final validator.  It extracts facts and pre-computes
safe, text-only comparisons.  Size, color/background, and placement are intentionally
not represented here because they are out of scope for the project.  Bold/continuous-
paragraph health-warning facts are left unknown when the input is text-only OCR.
"""

from __future__ import annotations

import json
import re
import unicodedata
import sys
import dataclasses

if sys.version_info < (3, 10):
    _orig_dataclass = dataclasses.dataclass
    def _patched_dataclass(*args, **kwargs):
        kwargs.pop("slots", None)
        return _orig_dataclass(*args, **kwargs)
    dataclasses.dataclass = _patched_dataclass

from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
try:
    from types import UnionType
except ImportError:
    class UnionType:
        pass
from typing import Any, Mapping, Protocol, Sequence, TypeVar, Union, get_args, get_origin, get_type_hints

from src.backend.extraction import distilled_spirits_label_dataclasses as ds
from src.backend.validators.distilled_spirits_label_rule_dicts import build_rule_result_dicts


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Public input / output helpers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class OcrTextBlock:
    """One OCR block.  Only `.text` is required.

    Position/confidence metadata is kept for traceability and future extensions,
    but this module does not use it for compliance because positioning is out of scope.
    """

    text: str
    block_id: str | None = None
    confidence: float | None = None
    reading_order: int | None = None
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ApplicationDetailParse:
    """Deterministic parse of the pasted TTB application detail page."""

    raw_text: str
    fields: dict[str, str] = field(default_factory=dict)
    sections: dict[str, list[str]] = field(default_factory=dict)
    principal_place_of_business_block: list[str] = field(default_factory=list)
    other_permit_block: list[str] = field(default_factory=list)
    contact_block: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PromptBundle:
    system_prompt: str
    user_prompt: str
    json_schema: dict[str, Any]


@dataclass(slots=True)
class ConstructionResult:
    review_input: ds.DistilledSpiritsLabelReviewInput
    parsed_application_detail: ApplicationDetailParse
    ocr_blocks: list[OcrTextBlock]
    application_prompt: PromptBundle | None = None
    label_prompt: PromptBundle | None = None
    application_llm_json: dict[str, Any] | None = None
    label_llm_json: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)


class JsonLlm(Protocol):
    """Tiny provider interface for a JSON-capable LLM.

    Implement this protocol with your model provider of choice.  The method should
    return a parsed JSON object, not a raw string.
    """

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


def construct_review_input(
    *,
    application_detail_text: str,
    ocr_text_blocks: Sequence[str | Mapping[str, Any] | OcrTextBlock],
    llm: JsonLlm | None = None,
    source_image_id: str | None = None,
    source_filename: str | None = None,
) -> ConstructionResult:
    """Construct the validator input dataclass from pasted application text and OCR.

    The deterministic pass always runs.  If `llm` is provided, it receives the
    deterministic seed and raw source material and can refine the extraction.
    Post-processing then re-applies safe deterministic checks so the downstream
    validator sees stable boolean facts when they are textually provable.
    """

    notes: list[str] = []
    parsed = parse_application_detail_text(application_detail_text)
    blocks = coerce_ocr_blocks(ocr_text_blocks)

    app_seed = build_application_seed(parsed)
    application_prompt: PromptBundle | None = None
    application_llm_json: dict[str, Any] | None = None

    if llm is not None:
        application_prompt = build_application_prompt(parsed, app_seed)
        application_llm_json = dict(
            llm.complete_json(
                system_prompt=application_prompt.system_prompt,
                user_prompt=application_prompt.user_prompt,
                json_schema=application_prompt.json_schema,
            )
        )
        application = dataclass_from_dict(ds.DistilledSpiritsApplication, application_llm_json)
        merge_application_seed(application, app_seed)
        notes.append("Application was refined by LLM and then deterministically post-processed.")
    else:
        application = app_seed
        notes.append("Application was built with deterministic parsing only; no LLM was supplied.")

    postprocess_application(application, parsed)

    label_seed = build_label_seed(blocks, application)
    label_prompt: PromptBundle | None = None
    label_llm_json: dict[str, Any] | None = None

    if llm is not None:
        label_prompt = build_label_prompt(blocks, application, label_seed)
        label_llm_json = dict(
            llm.complete_json(
                system_prompt=label_prompt.system_prompt,
                user_prompt=label_prompt.user_prompt,
                json_schema=label_prompt.json_schema,
            )
        )
        label = dataclass_from_dict(ds.DistilledSpiritsLabelExtraction, label_llm_json)
        merge_label_seed(label, label_seed)
        notes.append("Label extraction was refined by LLM and then deterministically post-processed.")
    else:
        label = label_seed
        notes.append("Label extraction was built with deterministic parsing only; no LLM was supplied.")

    postprocess_label(label, blocks, application)

    review = ds.DistilledSpiritsLabelReviewInput(
        application=application,
        label=label,
        source_image_id=source_image_id,
        source_filename=source_filename,
    )
    populate_precomputed_checks(review)

    return ConstructionResult(
        review_input=review,
        parsed_application_detail=parsed,
        ocr_blocks=blocks,
        application_prompt=application_prompt,
        label_prompt=label_prompt,
        application_llm_json=application_llm_json,
        label_llm_json=label_llm_json,
        notes=notes,
    )


def construct_application_from_detail(
    application_detail_text: str,
    llm: JsonLlm | None = None,
) -> tuple[ds.DistilledSpiritsApplication, ApplicationDetailParse, PromptBundle | None, dict[str, Any] | None]:
    """Construct only `DistilledSpiritsApplication` from the pasted application detail."""

    parsed = parse_application_detail_text(application_detail_text)
    seed = build_application_seed(parsed)
    prompt = None
    llm_json = None
    if llm is not None:
        prompt = build_application_prompt(parsed, seed)
        llm_json = dict(
            llm.complete_json(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                json_schema=prompt.json_schema,
            )
        )
        application = dataclass_from_dict(ds.DistilledSpiritsApplication, llm_json)
        merge_application_seed(application, seed)
    else:
        application = seed
    postprocess_application(application, parsed)
    return application, parsed, prompt, llm_json


def construct_label_from_ocr(
    ocr_text_blocks: Sequence[str | Mapping[str, Any] | OcrTextBlock],
    application: ds.DistilledSpiritsApplication,
    llm: JsonLlm | None = None,
) -> tuple[ds.DistilledSpiritsLabelExtraction, list[OcrTextBlock], PromptBundle | None, dict[str, Any] | None]:
    """Construct only `DistilledSpiritsLabelExtraction` from OCR text blocks."""

    blocks = coerce_ocr_blocks(ocr_text_blocks)
    seed = build_label_seed(blocks, application)
    prompt = None
    llm_json = None
    if llm is not None:
        prompt = build_label_prompt(blocks, application, seed)
        llm_json = dict(
            llm.complete_json(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
                json_schema=prompt.json_schema,
            )
        )
        label = dataclass_from_dict(ds.DistilledSpiritsLabelExtraction, llm_json)
        merge_label_seed(label, seed)
    else:
        label = seed
    postprocess_label(label, blocks, application)
    return label, blocks, prompt, llm_json


# ---------------------------------------------------------------------------
# Deterministic application parsing
# ---------------------------------------------------------------------------


_FIELD_LINE_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9/#()&.,'\- ]{1,90}):\s*(?P<value>.*)$")
_HELP_RE = re.compile(r"\bOpen\s+help\s+for\s+the\s+.*?\s+field\s+in\s+a\s+new\s+window\b", re.IGNORECASE)
_US_COUNTRY_VALUES = {
    "us",
    "usa",
    "u s a",
    "u.s.a",
    "u.s.a.",
    "united states",
    "united states of america",
}


FIELD_ALIASES = {
    "ttb id": "TTB ID",
    "status": "Status",
    "vendor code": "Vendor Code",
    "serial #": "Serial #",
    "serial number": "Serial #",
    "class/type code": "Class/Type Code",
    "origin code": "Origin Code",
    "brand name": "Brand Name",
    "fanciful name": "Fanciful Name",
    "type of application": "Type of Application",
    "for sale in": "For Sale In",
    "total bottle capacity": "Total Bottle Capacity",
    "wine vintage": "Wine Vintage",
    "formula": "Formula",
    "approval date": "Approval Date",
    "qualifications": "Qualifications",
    "plant registry/basic permit/brewers no (principal place of business)": "Plant Registry/Basic Permit/Brewers No (Principal Place of Business)",
    "plant registry/basic permit/brewers number (principal place of business)": "Plant Registry/Basic Permit/Brewers No (Principal Place of Business)",
    "plant registry/basic permit/brewers no (other)": "Plant Registry/Basic Permit/Brewers No (Other)",
    "contact information": "Contact Information",
    "phone number": "Phone Number",
    "fax number": "Fax Number",
}


def parse_application_detail_text(raw_text: str) -> ApplicationDetailParse:
    """Parse a COLA/application detail paste into key/value fields and sections."""

    text = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    # These UI artifacts show up in the copied page and are not application facts.
    text = re.sub(r"\barrow\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bPrintable\s+Version\b", " ", text, flags=re.IGNORECASE)

    parsed = ApplicationDetailParse(raw_text=raw_text)
    current_key: str | None = None

    for raw_line in text.split("\n"):
        line = clean_application_value(raw_line)
        if not line:
            continue

        match = _FIELD_LINE_RE.match(line)
        if match:
            key = canonical_application_field_name(match.group("key"))
            value = clean_application_value(match.group("value"))
            parsed.fields[key] = value
            parsed.sections.setdefault(key, [])
            current_key = key
            if value:
                parsed.sections[key].append(value)
            continue

        if current_key is not None:
            parsed.sections.setdefault(current_key, []).append(line)

    parsed.principal_place_of_business_block = parsed.sections.get(
        "Plant Registry/Basic Permit/Brewers No (Principal Place of Business)",
        [],
    )
    parsed.other_permit_block = parsed.sections.get("Plant Registry/Basic Permit/Brewers No (Other)", [])
    parsed.contact_block = parsed.sections.get("Contact Information", [])
    return parsed


def canonical_application_field_name(raw_key: str) -> str:
    raw = clean_application_value(raw_key).rstrip(":")
    return FIELD_ALIASES.get(raw.lower(), raw)


def clean_application_value(value: str | None) -> str:
    if value is None:
        return ""
    value = _HELP_RE.sub(" ", value)
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def build_application_seed(parsed: ApplicationDetailParse) -> ds.DistilledSpiritsApplication:
    """Build the best deterministic application seed from parsed application text."""

    fields_map = parsed.fields
    application = ds.DistilledSpiritsApplication()
    application.application_id = empty_to_none(fields_map.get("TTB ID"))
    application.identity.brand_name = empty_to_none(fields_map.get("Brand Name"))
    application.identity.class_type_designation = empty_to_none(fields_map.get("Class/Type Code"))

    infer_identity_from_class_type_code(application.identity, application.identity.class_type_designation)

    origin = empty_to_none(fields_map.get("Origin Code"))
    if origin:
        country = canonical_country_name(origin)
        application.country_of_origin = country
        application.identity.produced_country = country
        if is_us_country(country):
            application.import_status = ds.ImportStatus.DOMESTIC
        else:
            # A U.S. DSP/basic permit block commonly means the imported spirit is bottled/packed/filled
            # after importation.  If no U.S. permit block is present, keep the more conservative imported-
            # before-importation status.  The LLM may refine this when the paste provides better evidence.
            if parse_permit_block(parsed.principal_place_of_business_block) is not None:
                application.import_status = ds.ImportStatus.IMPORTED_BOTTLED_AFTER_IMPORTATION
            else:
                application.import_status = ds.ImportStatus.IMPORTED_BOTTLED_BEFORE_IMPORTATION

    capacity_ml = parse_net_contents_ml(fields_map.get("Total Bottle Capacity"))
    if capacity_ml is not None:
        application.net_contents.net_contents_ml = capacity_ml

    approval_date = parse_date_fuzzy(fields_map.get("Approval Date"))
    if approval_date is not None:
        application.extra_application_facts["approval_date"] = approval_date.isoformat()

    permit = parse_permit_block(parsed.principal_place_of_business_block)
    if permit is not None:
        role = ds.ResponsiblePartyRole.BOTTLER
        if application.import_status == ds.ImportStatus.IMPORTED_BOTTLED_BEFORE_IMPORTATION:
            role = ds.ResponsiblePartyRole.IMPORTER
        party = ds.ResponsiblePartyApplication(
            role=role,
            name=permit["company_name"],
            address=permit["address"],
            basic_permit_name=permit["company_name"],
            basic_permit_address=permit["address"],
            uses_principal_place_of_business=True,
        )
        application.responsible_parties.append(party)
        application.extra_application_facts["principal_place_of_business_permit_no"] = permit.get("permit_no")

    # Preserve raw application details for audit/debug and to give downstream validators access to fields
    # that have not yet received first-class dataclass slots.
    application.extra_application_facts.setdefault("raw_application_fields", dict(fields_map))
    application.extra_application_facts.setdefault("raw_application_sections", dict(parsed.sections))
    application.extra_application_facts.setdefault("fanciful_name", empty_to_none(fields_map.get("Fanciful Name")))
    application.extra_application_facts.setdefault("status", empty_to_none(fields_map.get("Status")))
    application.extra_application_facts.setdefault("serial_number", empty_to_none(fields_map.get("Serial #")))
    application.extra_application_facts.setdefault("vendor_code", empty_to_none(fields_map.get("Vendor Code")))
    application.extra_application_facts.setdefault("formula", empty_to_none(fields_map.get("Formula")))
    application.extra_application_facts.setdefault("type_of_application", empty_to_none(fields_map.get("Type of Application")))

    return application


def parse_permit_block(block: Sequence[str]) -> dict[str, Any] | None:
    """Parse a Principal Place of Business/basic permit block.

    Expected shape in the copied detail is usually:
        DSP-MD-18
        MONTEBELLO BRANDS, INC.
        1919 WILLOW SPRING RD
        BALTIMORE, MD 21222
    """

    lines = [clean_application_value(x) for x in block if clean_application_value(x)]
    if not lines:
        return None

    permit_no = None
    if re.search(r"\b(DSP|BWN|BR|PERMIT|[A-Z]{2,}-)[A-Z0-9-]+\b", lines[0], flags=re.IGNORECASE):
        permit_no = lines.pop(0)

    if not lines:
        return None

    company_name = lines.pop(0)
    address = parse_us_address_lines(lines)
    return {"permit_no": permit_no, "company_name": company_name, "address": address}


def parse_us_address_lines(lines: Sequence[str]) -> ds.Address:
    street_lines: list[str] = []
    city = state = postal = None
    country = "United States"

    for line in lines:
        city_match = re.match(r"^(?P<city>.+?),\s*(?P<state>[A-Z]{2})\s+(?P<postal>\d{5}(?:-\d{4})?)$", line)
        if city_match:
            city = city_match.group("city").title()
            state = city_match.group("state")
            postal = city_match.group("postal")
        else:
            street_lines.append(line.title())

    return ds.Address(
        street=" ".join(street_lines) or None,
        city=city,
        state_or_province=state,
        postal_code=postal,
        country=country if state else None,
    )


# ---------------------------------------------------------------------------
# Deterministic OCR parsing
# ---------------------------------------------------------------------------


_ABV_RE = re.compile(
    r"(?P<abv>\d{1,3}(?:\.\d+)?)\s*%?\s*(?:ALC(?:OHOL)?\.?\s*/?\s*(?:BY\s+)?VOL(?:UME)?\.?|ABV\b|ALCOHOL\s+BY\s+VOLUME)",
    re.IGNORECASE,
)
_BOTTLED_AT_ABV_RE = re.compile(
    r"BOTTLED\s+AT\s+\d{1,3}(?:\.\d+)?\s*%?\s*(?:ALC(?:OHOL)?\.?\s*/?\s*(?:BY\s+)?VOL(?:UME)?\.?|ABV\b|ALCOHOL\s+BY\s+VOLUME)",
    re.IGNORECASE,
)
_PROOF_RE = re.compile(r"(?P<proof>\d{1,3}(?:\.\d+)?)\s*(?:PROOF|PF)\b", re.IGNORECASE)
_NET_CONTENTS_RE = re.compile(
    r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>ML|M\s*L|MILLILIT(?:ER|RE)S?|L|LTR|LITER|LITRE|LITERS|LITRES)\b",
    re.IGNORECASE,
)
_GOV_WARNING_HEADER_RE = re.compile(r"\bGOVERNMENT\s+WARNING\s*:", re.IGNORECASE)
_FDC_YELLOW_5_RE = re.compile(r"\bCONTAINS\s+FD\s*&?\s*C\s+YELLOW\s*#?\s*5\b", re.IGNORECASE)
_SACCHARIN_RE = re.compile(r"\bCONTAINS\s+SACCHARIN\b", re.IGNORECASE)
_SULFITE_RE = re.compile(r"\bCONTAINS\s+(?:A\s+)?SULFIT(?:E|ING)\s+AGENT|\bCONTAINS\s+SULFITES\b", re.IGNORECASE)
_COLORING_RE = re.compile(
    r"\b(?:ARTIFICIALLY\s+COLORED|COLOU?RED\s+WITH\s+[A-Z0-9 #&,'\-]+|CERTIFIED\s+COLOR\s+ADDED|CARAMEL\s+(?:COLOR\s+)?ADDED)\b",
    re.IGNORECASE,
)
_WOOD_TREATMENT_RE = re.compile(r"\bCOLOU?RED\s+AND\s+FLAVO(?:U)?RED\s+WITH\s+WOOD\s+(?P<form>[A-Z]+)\b", re.IGNORECASE)
_COMMODITY_GROUP1_RE = re.compile(
    r"(?P<pct>\d{1,3}(?:\.\d+)?)\s*%\s+(?:(?P<commodity1>[A-Z]+)\s+)?NEUTRAL\s+SPIRITS(?:\s+DISTILLED\s+FROM\s+(?P<commodity2>[A-Z]+))?",
    re.IGNORECASE,
)
_COMMODITY_GROUP2_RE = re.compile(r"\bDISTILLED\s+FROM\s+(?P<commodity>[A-Z][A-Z\s-]{2,40})\b", re.IGNORECASE)
_RESPONSIBLE_PARTY_RE = re.compile(
    r"\b(?P<phrase>(?:IMPORTED|BOTTLED|DISTILLED|PRODUCED|MANUFACTURED|PACKED|FILLED|BLENDED|MADE|PREPARED)(?:\s+AND\s+(?:IMPORTED|BOTTLED|DISTILLED|PRODUCED|MANUFACTURED|PACKED|FILLED|BLENDED|MADE|PREPARED))*\s+BY|SOLE\s+U\.?\s*S\.?\s+AGENT|SOLE\s+AGENT)\b(?P<tail>[^\n]{0,180})",
    re.IGNORECASE,
)
_COUNTRY_ORIGIN_RE = re.compile(
    r"\b(?:PRODUCT|PRODUCE)\s+OF\s+(?P<country1>[A-Z][A-Z\s.'-]{2,40})\b|\bPRODUCED(?:\s+AND\s+BOTTLED)?\s+IN\s+(?P<country2>[A-Z][A-Z\s.'-]{2,40})\b|\bPRODUCED(?:\s+AND\s+BOTTLED)?\s+BY\s+[^\n,]+,?\s+(?P<country3>[A-Z][A-Z\s.'-]{2,40})\b",
    re.IGNORECASE,
)
_AGE_RE = re.compile(r"\b(?P<years>\d+(?:\.\d+)?|\d+\s*/\s*\d+|\d+½|\d+\s+1/2)\s+YEARS?\s+(?:OLD|AGED|OR\s+MORE\s+OLD)\b", re.IGNORECASE)
_DISTILLATION_DATE_RE = re.compile(r"\bDISTILLED\s+(?:ON\s+)?(?:IN\s+)?(?P<date>\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|[A-Z]+\s+\d{4})\b", re.IGNORECASE)
_STATE_DISTILLATION_RE = re.compile(r"\bDISTILLED\s+IN\s+(?P<state>[A-Z][A-Z\s]+)\b", re.IGNORECASE)

# A compact list for deterministic hints.  The LLM can handle the uncommon chart entries.
KNOWN_CLASS_TYPE_TERMS = [
    "straight bourbon whiskey",
    "straight bourbon whisky",
    "bourbon whiskey",
    "bourbon whisky",
    "straight rye whiskey",
    "straight rye whisky",
    "rye whiskey",
    "rye whisky",
    "straight wheat whiskey",
    "straight wheat whisky",
    "wheat whiskey",
    "wheat whisky",
    "straight malt whiskey",
    "straight malt whisky",
    "malt whiskey",
    "malt whisky",
    "straight corn whiskey",
    "straight corn whisky",
    "corn whiskey",
    "corn whisky",
    "blended whiskey",
    "blended whisky",
    "spirit whiskey",
    "spirit whisky",
    "light whiskey",
    "light whisky",
    "whiskey distilled from bourbon mash",
    "whisky distilled from bourbon mash",
    "vodka",
    "distilled gin",
    "redistilled gin",
    "compounded gin",
    "gin",
    "rum",
    "tequila",
    "mezcal",
    "mescal",
    "brandy",
    "fruit brandy",
    "apple brandy",
    "cognac",
    "armagnac",
    "liqueur",
    "cordial",
    "distilled spirits specialty",
]

US_STATE_NAMES = {
    "ALABAMA",
    "ALASKA",
    "ARIZONA",
    "ARKANSAS",
    "CALIFORNIA",
    "COLORADO",
    "CONNECTICUT",
    "DELAWARE",
    "FLORIDA",
    "GEORGIA",
    "HAWAII",
    "IDAHO",
    "ILLINOIS",
    "INDIANA",
    "IOWA",
    "KANSAS",
    "KENTUCKY",
    "LOUISIANA",
    "MAINE",
    "MARYLAND",
    "MASSACHUSETTS",
    "MICHIGAN",
    "MINNESOTA",
    "MISSISSIPPI",
    "MISSOURI",
    "MONTANA",
    "NEBRASKA",
    "NEVADA",
    "NEW HAMPSHIRE",
    "NEW JERSEY",
    "NEW MEXICO",
    "NEW YORK",
    "NORTH CAROLINA",
    "NORTH DAKOTA",
    "OHIO",
    "OKLAHOMA",
    "OREGON",
    "PENNSYLVANIA",
    "RHODE ISLAND",
    "SOUTH CAROLINA",
    "SOUTH DAKOTA",
    "TENNESSEE",
    "TEXAS",
    "UTAH",
    "VERMONT",
    "VIRGINIA",
    "WASHINGTON",
    "WEST VIRGINIA",
    "WISCONSIN",
    "WYOMING",
    "DISTRICT OF COLUMBIA",
}


def coerce_ocr_blocks(blocks: Sequence[str | Mapping[str, Any] | OcrTextBlock]) -> list[OcrTextBlock]:
    result: list[OcrTextBlock] = []
    for i, block in enumerate(blocks):
        if isinstance(block, OcrTextBlock):
            result.append(block)
            continue
        if isinstance(block, str):
            text = block
            result.append(OcrTextBlock(text=text, block_id=str(i), reading_order=i))
            continue
        if isinstance(block, Mapping):
            text = str(block.get("text") or block.get("content") or block.get("value") or "")
            bbox_value = block.get("bbox") or block.get("bounding_box")
            bbox = None
            if isinstance(bbox_value, Sequence) and not isinstance(bbox_value, (str, bytes)) and len(bbox_value) == 4:
                try:
                    bbox = tuple(float(x) for x in bbox_value)  # type: ignore[assignment]
                except (TypeError, ValueError):
                    bbox = None
            metadata = {str(k): v for k, v in block.items() if k not in {"text", "content", "value", "bbox", "bounding_box"}}
            result.append(
                OcrTextBlock(
                    text=text,
                    block_id=str(block.get("id") or block.get("block_id") or i),
                    confidence=as_float(block.get("confidence")),
                    reading_order=as_int(block.get("reading_order"), default=i),
                    page=as_int(block.get("page")),
                    bbox=bbox,
                    metadata=metadata,
                )
            )
    result.sort(key=lambda x: (x.page if x.page is not None else 0, x.reading_order if x.reading_order is not None else 0))
    return [b for b in result if b.text and b.text.strip()]


def build_label_seed(
    blocks: Sequence[OcrTextBlock],
    application: ds.DistilledSpiritsApplication,
) -> ds.DistilledSpiritsLabelExtraction:
    label = ds.DistilledSpiritsLabelExtraction()
    postprocess_label(label, list(blocks), application)
    return label


def postprocess_label(
    label: ds.DistilledSpiritsLabelExtraction,
    blocks: Sequence[OcrTextBlock],
    application: ds.DistilledSpiritsApplication,
) -> None:
    full_text = combined_ocr_text(blocks)
    normalized_full_text = normalize_whitespace(full_text)
    upper_full_text = normalized_full_text.upper()

    if not label.all_detected_text:
        label.all_detected_text = [
            ds.ExtractedText(text=b.text, normalized_text=normalize_whitespace(b.text), confidence=b.confidence, notes=f"block_id={b.block_id}")
            for b in blocks
        ]

    if label.overall_extraction_confidence is None:
        confidences = [b.confidence for b in blocks if b.confidence is not None]
        label.overall_extraction_confidence = sum(confidences) / len(confidences) if confidences else None

    # Brand name from application if the OCR contains it.
    app_brand = application.identity.brand_name
    if app_brand and not label.brand_name.value.is_present:
        matched = find_phrase_case_insensitive(full_text, app_brand)
        if matched:
            label.brand_name.value = ds.ExtractedText(text=matched, normalized_text=normalize_for_match(matched), confidence=0.95)
    if app_brand and label.brand_name.value.is_present:
        label.brand_name.matches_application_brand_name = names_match(label.brand_name.value.text, app_brand)

    # Class/type designation.  Prefer the LLM value if present; deterministic search fills gaps.
    if not label.class_type.statement.is_present:
        detected_class_type = find_class_type_term(full_text, application.identity.class_type_designation)
        if detected_class_type:
            label.class_type.statement = ds.ExtractedText(
                text=detected_class_type,
                normalized_text=normalize_for_match(detected_class_type),
                confidence=0.88,
            )
            label.class_type.declared_type = detected_class_type.lower().replace("whiskey", "whisky")
    if label.class_type.statement.is_present and application.identity.class_type_designation:
        label.class_type.matches_application_class_type = class_type_match(
            label.class_type.statement.text,
            application.identity.class_type_designation,
        )

    # Alcohol content / proof.
    abv = parse_abv_statement(full_text)
    if abv:
        statement, abv_percent = abv
        if not label.alcohol_content.statement.is_present:
            label.alcohol_content.statement = ds.ExtractedText(text=statement, normalized_text=normalize_whitespace(statement), confidence=0.98)
        if label.alcohol_content.abv_percent is None:
            label.alcohol_content.abv_percent = abv_percent
        label.alcohol_content.has_percent_alcohol_by_volume_phrase = True
        if application.alcohol.contains_solid_material:
            label.alcohol_content.uses_bottled_at_phrase_for_products_with_solids = bool(_BOTTLED_AT_ABV_RE.search(full_text))
    elif label.alcohol_content.abv_percent is None:
        label.alcohol_content.has_percent_alcohol_by_volume_phrase = False if "ABV" in upper_full_text or "ALC" in upper_full_text else None

    proof = parse_proof(full_text)
    if proof is not None and label.alcohol_content.proof is None:
        label.alcohol_content.proof = proof
    if label.alcohol_content.proof is not None and label.alcohol_content.proof_is_distinguished_from_abv_statement is None:
        label.alcohol_content.proof_is_distinguished_from_abv_statement = proof_appears_distinguished(full_text)

    if application.alcohol.abv_percent is not None and label.alcohol_content.abv_percent is not None:
        tolerance = application.alcohol.allowed_abv_tolerance_percent(application.net_contents.net_contents_ml)
        label.alcohol_content.matches_application_abv_with_tolerance = (
            abs(label.alcohol_content.abv_percent - application.alcohol.abv_percent) <= (tolerance or 0)
        )

    # Net contents.
    net = parse_net_contents_statement(full_text)
    if net:
        statement, ml = net
        if not label.net_contents.statement.is_present:
            label.net_contents.statement = ds.ExtractedText(text=statement, normalized_text=normalize_whitespace(statement), confidence=0.98)
        if label.net_contents.net_contents_ml is None:
            label.net_contents.net_contents_ml = ml
    if label.net_contents.net_contents_ml is not None:
        label.net_contents.is_metric_standard_of_fill = (
            label.net_contents.net_contents_ml in ds.CAN_STANDARD_FILLS_ML
            if application.net_contents.container_kind == ds.ContainerKind.CAN
            else label.net_contents.net_contents_ml in ds.NON_CAN_STANDARD_FILLS_ML
        )
    if application.net_contents.net_contents_ml is not None and label.net_contents.net_contents_ml is not None:
        label.net_contents.matches_application_net_contents = label.net_contents.net_contents_ml == application.net_contents.net_contents_ml

    # Responsible party statements.
    if not label.responsible_party_statements:
        label.responsible_party_statements = detect_responsible_party_statements(full_text)
    for stmt in label.responsible_party_statements:
        if stmt.phrase_is_appropriate is None and stmt.role_phrase:
            stmt.phrase_is_appropriate = role_phrase_is_appropriate(stmt.role_phrase, application.import_status)
        if stmt.name and application.responsible_parties and stmt.name_matches_basic_permit_or_application is None:
            stmt.name_matches_basic_permit_or_application = any(names_match(stmt.name, p.name) for p in application.responsible_parties)
        if application.import_status == ds.ImportStatus.IMPORTED_BOTTLED_AFTER_IMPORTATION and stmt.us_bottling_packing_or_filling_indicated_for_import is None:
            stmt.us_bottling_packing_or_filling_indicated_for_import = any(
                role in stmt.roles for role in [ds.ResponsiblePartyRole.BOTTLER, ds.ResponsiblePartyRole.PACKER, ds.ResponsiblePartyRole.FILLER]
            )

    # Country of origin.
    if not label.country_of_origin.statement.is_present:
        country_statement = detect_country_origin_statement(full_text, application.country_of_origin)
        if country_statement:
            statement, country = country_statement
            label.country_of_origin.statement = ds.ExtractedText(text=statement, normalized_text=normalize_whitespace(statement), confidence=0.92)
            label.country_of_origin.country = country
    if label.country_of_origin.statement.is_present and label.country_of_origin.accepted_format is None:
        label.country_of_origin.accepted_format = bool(_COUNTRY_ORIGIN_RE.search(label.country_of_origin.statement.text or ""))
    if application.country_of_origin and label.country_of_origin.country:
        label.country_of_origin.matches_application_country = country_match(label.country_of_origin.country, application.country_of_origin)

    # Coloring materials.
    if not label.coloring_disclosure.statement.is_present:
        match = _COLORING_RE.search(full_text)
        if match:
            text = match.group(0).strip()
            label.coloring_disclosure.statement = ds.ExtractedText(text=text, normalized_text=normalize_whitespace(text), confidence=0.90)
            label.coloring_disclosure.uses_artificially_colored_phrase = "ARTIFICIALLY COLORED" in text.upper()
            label.coloring_disclosure.disclosed_materials = detect_coloring_materials(text)
    if application.disclosures.contains_coloring_materials and label.coloring_disclosure.discloses_required_coloring_materials is None:
        label.coloring_disclosure.discloses_required_coloring_materials = label.coloring_disclosure.statement.is_present

    # Wood treatment.
    if not label.wood_treatment_disclosure.statement.is_present:
        match = _WOOD_TREATMENT_RE.search(full_text)
        if match:
            text = match.group(0).strip()
            label.wood_treatment_disclosure.statement = ds.ExtractedText(text=text, normalized_text=normalize_whitespace(text), confidence=0.95)
            label.wood_treatment_disclosure.wood_form = match.group("form").lower()
            label.wood_treatment_disclosure.contains_colored_and_flavored_with_wood_phrase = True
    if application.disclosures.wood_treatment_exception_applies is not None and label.wood_treatment_disclosure.exception_applies is None:
        label.wood_treatment_disclosure.exception_applies = application.disclosures.wood_treatment_exception_applies

    # FD&C Yellow #5.
    if not label.fdc_yellow_5_disclosure.statement.is_present:
        match = _FDC_YELLOW_5_RE.search(full_text)
        if match:
            text = match.group(0).strip()
            label.fdc_yellow_5_disclosure.statement = ds.ExtractedText(text=text, normalized_text=normalize_whitespace(text), confidence=0.98)
            label.fdc_yellow_5_disclosure.contains_required_phrase = True
    elif label.fdc_yellow_5_disclosure.contains_required_phrase is None:
        label.fdc_yellow_5_disclosure.contains_required_phrase = bool(_FDC_YELLOW_5_RE.search(label.fdc_yellow_5_disclosure.statement.text or ""))

    # Saccharin.
    if not label.saccharin_disclosure.statement.is_present:
        saccharin_text = detect_exact_or_keyword_statement(full_text, ds.SACCHARIN_DISCLOSURE_TEXT, _SACCHARIN_RE)
        if saccharin_text:
            label.saccharin_disclosure.statement = ds.ExtractedText(text=saccharin_text, normalized_text=normalize_whitespace(saccharin_text), confidence=0.96)
    if label.saccharin_disclosure.statement.is_present:
        label.saccharin_disclosure.exact_required_text_present = contains_normalized_text(full_text, ds.SACCHARIN_DISCLOSURE_TEXT, case_sensitive=False)

    # Sulfites.
    if not label.sulfite_declaration.statement.is_present:
        match = _SULFITE_RE.search(full_text)
        if match:
            text = match.group(0).strip()
            label.sulfite_declaration.statement = ds.ExtractedText(text=text, normalized_text=normalize_whitespace(text), confidence=0.96)
    if label.sulfite_declaration.statement.is_present:
        text_upper = (label.sulfite_declaration.statement.text or "").upper()
        label.sulfite_declaration.contains_sulfites_phrase_present = "CONTAINS SULFITES" in text_upper
        label.sulfite_declaration.contains_sulfiting_agents_phrase_present = "SULFITING AGENT" in text_upper
        label.sulfite_declaration.specific_sulfiting_agents_declared = bool(re.search(r"SULFUR\s+DIOXIDE|POTASSIUM\s+METABISULFITE|SODIUM\s+BISULFITE", text_upper))

    # Commodity statement.
    if not label.commodity_statement.statement.is_present:
        commodity_statement = detect_commodity_statement(full_text)
        if commodity_statement:
            statement, group, pct, commodity = commodity_statement
            label.commodity_statement.statement = ds.ExtractedText(text=statement, normalized_text=normalize_whitespace(statement), confidence=0.92)
            label.commodity_statement.detected_group = group
            label.commodity_statement.neutral_spirits_percent = pct
            label.commodity_statement.neutral_spirit_commodity = commodity
    if label.commodity_statement.detected_group == ds.CommodityStatementGroup.GROUP_1_PERCENT_AND_COMMODITY:
        label.commodity_statement.group1_percent_and_commodity_present = True
    if label.commodity_statement.detected_group == ds.CommodityStatementGroup.GROUP_2_COMMODITY_ONLY:
        label.commodity_statement.group2_distilled_from_commodity_present = True
    if application.commodity_statement.neutral_spirit_commodity and label.commodity_statement.neutral_spirit_commodity:
        label.commodity_statement.matches_application_commodity = commodity_match(
            label.commodity_statement.neutral_spirit_commodity,
            application.commodity_statement.neutral_spirit_commodity,
        )
    if application.commodity_statement.neutral_spirits_percent is not None and label.commodity_statement.neutral_spirits_percent is not None:
        label.commodity_statement.matches_application_neutral_spirits_percent = abs(
            application.commodity_statement.neutral_spirits_percent - label.commodity_statement.neutral_spirits_percent
        ) < 0.01

    # Age statement and age-triggering label facts.
    if not label.age_statement.statement.is_present:
        age = detect_age_statement(full_text)
        if age:
            statement, months = age
            label.age_statement.statement = ds.ExtractedText(text=statement, normalized_text=normalize_whitespace(statement), confidence=0.88)
            label.age_statement.stated_age_months = months
    if label.age_statement.statement.is_present:
        label.age_statement.uses_years_old_or_aged_years_format = bool(_AGE_RE.search(label.age_statement.statement.text or ""))
    if application.age.age_statement_required_by_age() is not None:
        required = application.age.age_statement_required_by_age()
        label.age_statement.required_age_statement_present = bool(label.age_statement.statement.is_present) if required else True
    if application.age.youngest_component_age_months is not None and label.age_statement.stated_age_months is not None:
        label.age_statement.age_is_not_overstated = label.age_statement.stated_age_months <= application.age.youngest_component_age_months
    if label.has_distillation_date is None:
        label.has_distillation_date = bool(_DISTILLATION_DATE_RE.search(full_text))
    if label.has_distillation_date and not label.distillation_date_text.is_present:
        date_match = _DISTILLATION_DATE_RE.search(full_text)
        if date_match:
            label.distillation_date_text = ds.ExtractedText(text=date_match.group(0), normalized_text=normalize_whitespace(date_match.group(0)), confidence=0.90)

    # State of distillation.
    if not label.state_of_distillation.statement.is_present:
        match = _STATE_DISTILLATION_RE.search(full_text)
        if match:
            state = clean_detected_state(match.group("state"))
            if state:
                statement = match.group(0).strip()
                label.state_of_distillation.statement = ds.ExtractedText(text=statement, normalized_text=normalize_whitespace(statement), confidence=0.90)
                label.state_of_distillation.state = state
                label.state_of_distillation.accepted_format = True
    if application.state_of_distillation.actual_state_of_distillation and label.state_of_distillation.state:
        label.state_of_distillation.matches_application_state = state_match(
            label.state_of_distillation.state,
            application.state_of_distillation.actual_state_of_distillation,
        )

    # Government warning.
    postprocess_government_warning(label.government_warning, full_text)

    # Extraction notes for the validator/debug UI.
    label.extra_extracted_facts.setdefault("raw_ocr_text", full_text)
    label.extra_extracted_facts.setdefault("ocr_block_count", len(blocks))
    label.extra_extracted_facts.setdefault(
        "text_only_limitations",
        "Text-only OCR cannot establish text size, color/background contrast, physical location, or bold/non-bold style.",
    )


def combined_ocr_text(blocks: Sequence[OcrTextBlock]) -> str:
    return "\n".join(b.text for b in blocks if b.text and b.text.strip())


def parse_abv_statement(text: str) -> tuple[str, float] | None:
    match = _ABV_RE.search(text)
    if not match:
        return None
    return match.group(0).strip(), float(match.group("abv"))


def parse_proof(text: str) -> float | None:
    match = _PROOF_RE.search(text)
    return float(match.group("proof")) if match else None


def parse_net_contents_statement(text: str) -> tuple[str, int] | None:
    match = _NET_CONTENTS_RE.search(text or "")
    if not match:
        return None
    amount = float(match.group("amount"))
    unit = re.sub(r"\s+", "", match.group("unit").upper())
    ml = int(round(amount * 1000)) if unit in {"L", "LTR", "LITER", "LITRE", "LITERS", "LITRES"} else int(round(amount))
    return match.group(0).strip(), ml


def parse_net_contents_ml(text: str | None) -> int | None:
    if not text:
        return None
    result = parse_net_contents_statement(text)
    if result:
        return result[1]
    bare = re.match(r"^\s*(\d+(?:\.\d+)?)\s*$", text)
    if bare:
        return int(round(float(bare.group(1))))
    return None


def proof_appears_distinguished(text: str) -> bool | None:
    match = _PROOF_RE.search(text)
    if not match:
        return None
    start, end = match.span()
    before = text[max(0, start - 2) : start]
    after = text[end : min(len(text), end + 2)]
    return any(ch in before + after for ch in "()[]{}·•,-;")


def find_class_type_term(text: str, application_class_type: str | None) -> str | None:
    candidates: list[str] = []
    if application_class_type:
        candidates.append(application_class_type)
        normalized = application_class_type.lower().replace("whiskey", "whisky")
        if "rum" in normalized:
            candidates.append("rum")
        if "vodka" in normalized:
            candidates.append("vodka")
        if "gin" in normalized:
            candidates.append("gin")
        if "brandy" in normalized:
            candidates.append("brandy")
        if "whisky" in normalized:
            candidates.extend(["whisky", "whiskey"])
    candidates.extend(KNOWN_CLASS_TYPE_TERMS)

    best: str | None = None
    best_len = 0
    for candidate in candidates:
        if not candidate:
            continue
        matched = find_phrase_case_insensitive(text, candidate)
        if matched and len(matched) > best_len:
            best = matched
            best_len = len(matched)
    return best


def detect_responsible_party_statements(text: str) -> list[ds.ResponsiblePartyLabelStatement]:
    statements: list[ds.ResponsiblePartyLabelStatement] = []
    for match in _RESPONSIBLE_PARTY_RE.finditer(text):
        phrase = normalize_whitespace(match.group("phrase"))
        tail = normalize_whitespace(match.group("tail"))
        raw = normalize_whitespace(f"{phrase} {tail}".strip())
        roles = roles_from_phrase(phrase)
        name = parse_company_name_after_phrase(tail)
        statements.append(
            ds.ResponsiblePartyLabelStatement(
                statement=ds.ExtractedText(text=raw, normalized_text=normalize_whitespace(raw), confidence=0.82),
                role_phrase=phrase.upper(),
                roles=roles,
                name=name,
            )
        )
    return statements


def roles_from_phrase(phrase: str) -> list[ds.ResponsiblePartyRole]:
    p = phrase.upper()
    roles: list[ds.ResponsiblePartyRole] = []
    mapping = [
        ("IMPORTED", ds.ResponsiblePartyRole.IMPORTER),
        ("BOTTLED", ds.ResponsiblePartyRole.BOTTLER),
        ("PACKED", ds.ResponsiblePartyRole.PACKER),
        ("FILLED", ds.ResponsiblePartyRole.FILLER),
        ("DISTILLED", ds.ResponsiblePartyRole.DISTILLER),
        ("BLENDED", ds.ResponsiblePartyRole.BLENDER),
        ("MADE", ds.ResponsiblePartyRole.MAKER),
        ("PREPARED", ds.ResponsiblePartyRole.PREPARER),
        ("MANUFACTURED", ds.ResponsiblePartyRole.MANUFACTURER),
        ("PRODUCED", ds.ResponsiblePartyRole.PRODUCER),
        ("SOLE", ds.ResponsiblePartyRole.SOLE_AGENT),
    ]
    for token, role in mapping:
        if token in p and role not in roles:
            roles.append(role)
    return roles


def parse_company_name_after_phrase(tail: str) -> str | None:
    tail = normalize_whitespace(tail)
    if not tail:
        return None
    # Keep up to first likely address separator.  LLM can do better when needed.
    parts = re.split(r"\s{2,}|,\s*(?=\d|[A-Z][a-z]+,?\s+[A-Z]{2}\b)|\b\d{1,5}\s+", tail, maxsplit=1)
    name = parts[0].strip(" ,.;:-")
    return name or None


def role_phrase_is_appropriate(phrase: str, import_status: ds.ImportStatus) -> bool | None:
    roles = set(roles_from_phrase(phrase))
    if import_status == ds.ImportStatus.DOMESTIC:
        return bool(
            roles
            & {
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
    if import_status == ds.ImportStatus.IMPORTED_BOTTLED_BEFORE_IMPORTATION:
        return bool(roles & {ds.ResponsiblePartyRole.IMPORTER, ds.ResponsiblePartyRole.SOLE_AGENT})
    if import_status == ds.ImportStatus.IMPORTED_BOTTLED_AFTER_IMPORTATION:
        return bool(
            roles
            & {
                ds.ResponsiblePartyRole.IMPORTER,
                ds.ResponsiblePartyRole.BOTTLER,
                ds.ResponsiblePartyRole.PACKER,
                ds.ResponsiblePartyRole.FILLER,
            }
        )
    return None


def detect_country_origin_statement(text: str, expected_country: str | None = None) -> tuple[str, str] | None:
    for match in _COUNTRY_ORIGIN_RE.finditer(text):
        country = match.group("country1") or match.group("country2") or match.group("country3")
        country = trim_country_capture(country)
        if expected_country is None or country_match(country, expected_country):
            return normalize_whitespace(match.group(0)), country
    if expected_country:
        matched = find_phrase_case_insensitive(text, expected_country)
        if matched:
            return matched, canonical_country_name(matched)
    return None


def trim_country_capture(country: str) -> str:
    country = normalize_whitespace(country).strip(" .,:;-")
    country = re.split(r"\b(?:NET|ALC|VOL|BOTTLED|IMPORTED|GOVERNMENT|WARNING)\b", country, maxsplit=1, flags=re.IGNORECASE)[0]
    return canonical_country_name(country)


def detect_coloring_materials(text: str) -> list[str]:
    materials = []
    upper = text.upper()
    for token in ["CARAMEL", "CERTIFIED COLOR", "GRAPESKIN EXTRACT", "ANNATTO", "FD&C YELLOW #5"]:
        if token in upper:
            materials.append(token.title().replace("Fd&C", "FD&C"))
    if not materials and "ARTIFICIALLY COLORED" in upper:
        materials.append("Artificial color")
    return materials


def detect_exact_or_keyword_statement(text: str, exact_text: str, keyword_re: re.Pattern[str]) -> str | None:
    if contains_normalized_text(text, exact_text, case_sensitive=False):
        return exact_text
    match = keyword_re.search(text)
    if not match:
        return None
    start = max(0, match.start() - 120)
    end = min(len(text), match.end() + 180)
    return normalize_whitespace(text[start:end]).strip()


def detect_commodity_statement(text: str) -> tuple[str, ds.CommodityStatementGroup, float | None, str | None] | None:
    match = _COMMODITY_GROUP1_RE.search(text)
    if match:
        commodity = match.group("commodity1") or match.group("commodity2")
        return (
            normalize_whitespace(match.group(0)),
            ds.CommodityStatementGroup.GROUP_1_PERCENT_AND_COMMODITY,
            float(match.group("pct")),
            commodity.lower() if commodity else None,
        )
    match = _COMMODITY_GROUP2_RE.search(text)
    if match:
        commodity = normalize_whitespace(match.group("commodity")).lower().strip(" .,:;-")
        return (
            normalize_whitespace(match.group(0)),
            ds.CommodityStatementGroup.GROUP_2_COMMODITY_ONLY,
            None,
            commodity,
        )
    return None


def detect_age_statement(text: str) -> tuple[str, int] | None:
    match = _AGE_RE.search(text)
    if not match:
        return None
    months = years_text_to_months(match.group("years"))
    return normalize_whitespace(match.group(0)), months


def years_text_to_months(text: str) -> int:
    clean = text.strip().replace("½", ".5")
    if "/" in clean:
        if " " in clean:
            whole, frac = clean.split(" ", 1)
            num, den = frac.split("/", 1)
            years = float(whole) + float(num) / float(den)
        else:
            num, den = clean.split("/", 1)
            years = float(num) / float(den)
    else:
        years = float(clean)
    return int(round(years * 12))


def clean_detected_state(raw: str) -> str | None:
    state = normalize_whitespace(raw).strip(" .,:;-").upper()
    for stop in [" BOTTLED", " PRODUCED", " GOVERNMENT", " ALC", " VOL", " NET"]:
        if stop in state:
            state = state.split(stop, 1)[0].strip()
    if state in US_STATE_NAMES:
        return state.title()
    # Also allow state names embedded before class/type, e.g. "KENTUCKY STRAIGHT BOURBON".
    for name in sorted(US_STATE_NAMES, key=len, reverse=True):
        if state.startswith(name):
            return name.title()
    return None


def postprocess_government_warning(warning: ds.GovernmentWarningLabel, full_text: str) -> None:
    required = ds.GOVERNMENT_WARNING_FULL_TEXT
    exact_present = contains_normalized_text(full_text, required, case_sensitive=True)
    text_present_case_insensitive = contains_normalized_text(full_text, required, case_sensitive=False)
    header_match = _GOV_WARNING_HEADER_RE.search(full_text)

    if header_match and not warning.header_text.is_present:
        # Preserve what OCR actually produced for the header.
        warning.header_text = ds.ExtractedText(
            text=normalize_whitespace(header_match.group(0).rstrip(":")),
            normalized_text=normalize_whitespace(header_match.group(0).rstrip(":")),
            confidence=0.98,
        )

    if exact_present and not warning.full_text.is_present:
        warning.full_text = ds.ExtractedText(text=required, normalized_text=normalize_whitespace(required), confidence=0.99)
        warning.body_text = ds.ExtractedText(text=ds.GOVERNMENT_WARNING_BODY, normalized_text=normalize_whitespace(ds.GOVERNMENT_WARNING_BODY), confidence=0.99)
    elif text_present_case_insensitive and not warning.full_text.is_present:
        snippet = extract_warning_snippet(full_text) or required
        warning.full_text = ds.ExtractedText(text=snippet, normalized_text=normalize_whitespace(snippet), confidence=0.90)

    if warning.header_is_exact_all_caps is None:
        warning.header_is_exact_all_caps = bool(re.search(r"\bGOVERNMENT\s+WARNING\s*:", full_text))
    if warning.exact_required_text_present is None:
        warning.exact_required_text_present = exact_present

    # Text-only OCR cannot prove boldness or paragraph continuity.  Leave unknown unless an LLM/OCR
    # adapter explicitly provided these facts before post-processing.
    if warning.government_warning_compliant is None:
        if warning.exact_required_text_present is True and warning.header_is_exact_all_caps is True:
            if warning.header_is_bold is False or warning.body_is_not_bold is False or warning.appears_as_continuous_paragraph is False:
                warning.government_warning_compliant = False
            elif warning.header_is_bold is True and warning.body_is_not_bold is True and warning.appears_as_continuous_paragraph is True:
                warning.government_warning_compliant = True
            else:
                warning.government_warning_compliant = None
        elif warning.full_text.is_present or header_match:
            warning.government_warning_compliant = False


def extract_warning_snippet(text: str) -> str | None:
    header = _GOV_WARNING_HEADER_RE.search(text)
    if not header:
        return None
    tail = text[header.start() :]
    end_match = re.search(r"health\s+problems\s*\.?", tail, flags=re.IGNORECASE)
    if end_match:
        return normalize_whitespace(tail[: end_match.end()])
    return normalize_whitespace(tail[:600])


# ---------------------------------------------------------------------------
# Application post-processing and inference
# ---------------------------------------------------------------------------


def postprocess_application(application: ds.DistilledSpiritsApplication, parsed: ApplicationDetailParse) -> None:
    fields_map = parsed.fields

    application.application_id = application.application_id or empty_to_none(fields_map.get("TTB ID"))
    application.identity.brand_name = application.identity.brand_name or empty_to_none(fields_map.get("Brand Name"))
    application.identity.class_type_designation = application.identity.class_type_designation or empty_to_none(fields_map.get("Class/Type Code"))
    application.country_of_origin = application.country_of_origin or empty_to_none(fields_map.get("Origin Code"))
    if application.country_of_origin:
        application.country_of_origin = canonical_country_name(application.country_of_origin)
        application.identity.produced_country = application.identity.produced_country or application.country_of_origin

    if application.identity.class_type_designation:
        infer_identity_from_class_type_code(application.identity, application.identity.class_type_designation)
        infer_commodity_group(application)
        infer_age_flags(application)
        infer_state_of_distillation_flags(application)

    if application.net_contents.net_contents_ml is None:
        application.net_contents.net_contents_ml = parse_net_contents_ml(fields_map.get("Total Bottle Capacity"))

    if application.country_of_origin:
        if is_us_country(application.country_of_origin):
            application.import_status = ds.ImportStatus.DOMESTIC
        elif application.import_status == ds.ImportStatus.DOMESTIC:
            if application.responsible_parties:
                application.import_status = ds.ImportStatus.IMPORTED_BOTTLED_AFTER_IMPORTATION
            else:
                application.import_status = ds.ImportStatus.IMPORTED_BOTTLED_BEFORE_IMPORTATION

    if not application.responsible_parties:
        permit = parse_permit_block(parsed.principal_place_of_business_block)
        if permit is not None:
            application.responsible_parties.append(
                ds.ResponsiblePartyApplication(
                    role=ds.ResponsiblePartyRole.BOTTLER,
                    name=permit["company_name"],
                    address=permit["address"],
                    basic_permit_name=permit["company_name"],
                    basic_permit_address=permit["address"],
                    uses_principal_place_of_business=True,
                )
            )
            application.extra_application_facts.setdefault("principal_place_of_business_permit_no", permit.get("permit_no"))

    application.extra_application_facts.setdefault("raw_application_fields", dict(fields_map))
    application.extra_application_facts.setdefault("raw_application_sections", dict(parsed.sections))
    application.extra_application_facts.setdefault("construction_limitations", [])
    if application.alcohol.abv_percent is None:
        application.extra_application_facts["construction_limitations"].append(
            "Application detail paste did not expose an application ABV; ABV match checks stay unknown unless another source supplies it."
        )


def infer_identity_from_class_type_code(identity: ds.ProductIdentityApplication, code: str | None) -> None:
    if not code:
        return
    normalized = normalize_for_match(code).replace("whiskey", "whisky")
    identity.class_type_designation = identity.class_type_designation or code

    if "rum" in normalized:
        identity.class_name = identity.class_name or "rum"
        identity.type_name = identity.type_name or "rum"
    if "vodka" in normalized:
        identity.class_name = identity.class_name or "neutral spirits or alcohol"
        identity.type_name = identity.type_name or "vodka"
    if "gin" in normalized:
        identity.class_name = identity.class_name or "gin"
        identity.type_name = identity.type_name or "gin"
    if "brandy" in normalized or "cognac" in normalized or "armagnac" in normalized:
        identity.class_name = identity.class_name or "brandy"
        identity.type_name = identity.type_name or ("cognac" if "cognac" in normalized else "brandy")
        identity.is_brandy = True
    if "whisky" in normalized:
        identity.class_name = identity.class_name or "whisky"
        identity.type_name = identity.type_name or first_matching_whisky_type(normalized) or "whisky"
        identity.is_whisky = True
    if "flavored" in normalized or "flavour" in normalized:
        identity.is_flavored = True
    if "specialty" in normalized or "speciality" in normalized or "other" in normalized:
        identity.is_distilled_spirits_specialty = True

    if identity.type_name and identity.class_type_designation is None:
        identity.class_type_designation = identity.type_name


def first_matching_whisky_type(normalized: str) -> str | None:
    types = sorted(ds.STATE_OF_DISTILLATION_WHISKY_TYPES, key=len, reverse=True)
    for value in types:
        if value in normalized:
            return value
        if value.replace("whisky", "whiskey") in normalized:
            return value
    return None


def infer_commodity_group(application: ds.DistilledSpiritsApplication) -> None:
    if application.commodity_statement.group != ds.CommodityStatementGroup.NONE:
        return
    designation = normalize_for_match(application.identity.class_type_designation or application.identity.type_name or "").replace("whiskey", "whisky")
    group1_terms = [
        "blended whisky",
        "whisky a blend",
        "blended bourbon whisky",
        "blended wheat whisky",
        "blended rye whisky",
        "blended malt whisky",
        "blended rye malt whisky",
        "blended corn whisky",
        "spirit whisky",
        "compounded gin",
        "redistilled gin",
        "blended applejack",
    ]
    group2_terms = ["distilled gin"]
    if any(term in designation for term in group1_terms):
        application.commodity_statement.group = ds.CommodityStatementGroup.GROUP_1_PERCENT_AND_COMMODITY
    elif any(term in designation for term in group2_terms):
        application.commodity_statement.group = ds.CommodityStatementGroup.GROUP_2_COMMODITY_ONLY
    elif any(term in designation for term in ["vodka", "neutral spirits", "alcohol", "grain spirits"]):
        application.commodity_statement.neutral_spirit_distillation_method = ds.NeutralSpiritDistillationMethod.UNKNOWN


def infer_age_flags(application: ds.DistilledSpiritsApplication) -> None:
    designation = normalize_for_match(application.identity.class_type_designation or application.identity.type_name or "").replace("whiskey", "whisky")
    application.age.is_any_whisky_type = application.age.is_any_whisky_type or "whisky" in designation
    application.age.is_grape_lees_brandy = application.age.is_grape_lees_brandy or "grape lees brandy" in designation
    application.age.is_grape_pomace_or_marc_brandy = application.age.is_grape_pomace_or_marc_brandy or (
        "grape pomace brandy" in designation or "grape marc brandy" in designation
    )


def infer_state_of_distillation_flags(application: ds.DistilledSpiritsApplication) -> None:
    designation = (application.identity.type_name or application.identity.class_type_designation or "").lower().replace("whiskey", "whisky")
    if designation in ds.STATE_OF_DISTILLATION_WHISKY_TYPES or any(t in designation for t in ds.STATE_OF_DISTILLATION_WHISKY_TYPES):
        application.state_of_distillation.whisky_type = application.state_of_distillation.whisky_type or designation
        if is_us_country(application.country_of_origin or application.identity.produced_country):
            application.state_of_distillation.produced_in_united_states = True
            application.identity.is_us_produced_whisky = True


# ---------------------------------------------------------------------------
# LLM prompts
# ---------------------------------------------------------------------------


def build_application_prompt(parsed: ApplicationDetailParse, seed: ds.DistilledSpiritsApplication) -> PromptBundle:
    schema = dataclass_json_schema(ds.DistilledSpiritsApplication)
    system_prompt = (
        "You construct a DistilledSpiritsApplication JSON object from pasted TTB COLA/application detail text. "
        "Return only JSON that conforms to the supplied schema. Do not use markdown. "
        "Preserve exact source values in first-class fields when possible and in extra_application_facts when no slot exists. "
        "Use null for unknown values. Do not invent ABV, net contents, disclosures, age facts, or production facts not supported by the text. "
        "Conservative normalization is allowed: map Origin Code to country_of_origin, Brand Name to identity.brand_name, "
        "Class/Type Code to identity.class_type_designation/class/type hints, and Plant Registry/Basic Permit block to responsible_parties. "
        "If an origin country is not the United States, mark import_status as an imported status only when supported by the paste; otherwise use the deterministic seed."
    )
    user_prompt = json.dumps(
        {
            "task": "Build DistilledSpiritsApplication from application detail text.",
            "application_detail_text": parsed.raw_text,
            "deterministic_parse": dataclass_to_dict(parsed, include_none=False),
            "deterministic_seed": dataclass_to_dict(seed, include_none=False),
            "important_rules": [
                "Only populate fields that are application/product facts, not label OCR facts.",
                "The Status field is administrative; preserve it in extra_application_facts.status, not as a compliance failure.",
                "If Total Bottle Capacity is blank, leave net_contents.net_contents_ml null.",
                "If ABV is absent, leave alcohol.abv_percent null.",
            ],
        },
        indent=2,
        sort_keys=True,
    )
    return PromptBundle(system_prompt=system_prompt, user_prompt=user_prompt, json_schema=schema)


def build_label_prompt(
    blocks: Sequence[OcrTextBlock],
    application: ds.DistilledSpiritsApplication,
    seed: ds.DistilledSpiritsLabelExtraction,
) -> PromptBundle:
    schema = dataclass_json_schema(ds.DistilledSpiritsLabelExtraction)
    system_prompt = (
        "You construct a DistilledSpiritsLabelExtraction JSON object from OCR text blocks. "
        "Return only JSON that conforms to the supplied schema. Do not use markdown. "
        "Your job is extraction, not final legal validation. Preserve exact OCR text in ExtractedText.text. "
        "Use null for unknown values and do not guess a field is present unless the OCR text supports it. "
        "Resolve booleans only when the OCR text and application facts make the answer clear. "
        "Ignore text size, color/background contrast, and placement/location. "
        "Because the input is text-only OCR, leave boldness and continuous-paragraph health-warning fields null unless the OCR metadata explicitly proves them. "
        "For the government warning, exact wording and all-caps header may be evaluated from text. "
        "When comparing names/class/type, tolerate capitalization and punctuation differences but not materially different words."
    )
    user_prompt = json.dumps(
        {
            "task": "Build DistilledSpiritsLabelExtraction from OCR text blocks.",
            "application_context": dataclass_to_dict(application, include_none=False),
            "ocr_blocks": [dataclass_to_dict(b, include_none=False) for b in blocks],
            "combined_ocr_text": combined_ocr_text(blocks),
            "deterministic_seed": dataclass_to_dict(seed, include_none=False),
            "required_government_warning_text": ds.GOVERNMENT_WARNING_FULL_TEXT,
            "important_rules": [
                "Brand name, class/type designation, alcohol content, net contents, responsible party/name-address, and government warning are core text fields.",
                "Country of origin is required only for imported spirits; extract it when visible.",
                "Extract conditional disclosures only when visible or when application facts make a missing disclosure provable.",
                "Do not mark absent optional disclosures as noncompliant; validators decide applicability from application facts.",
                "Do not populate any out-of-scope size/color/position fields.",
            ],
        },
        indent=2,
        sort_keys=True,
    )
    return PromptBundle(system_prompt=system_prompt, user_prompt=user_prompt, json_schema=schema)


# ---------------------------------------------------------------------------
# Dataclass JSON codec and JSON Schema generator
# ---------------------------------------------------------------------------


def dataclass_to_dict(obj: Any, *, include_none: bool = True) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {}
        for f in fields(obj):
            value = getattr(obj, f.name)
            encoded = dataclass_to_dict(value, include_none=include_none)
            if include_none or encoded not in (None, [], {}, ""):
                result[f.name] = encoded
        return result
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, list):
        return [dataclass_to_dict(v, include_none=include_none) for v in obj if include_none or v is not None]
    if isinstance(obj, tuple):
        return [dataclass_to_dict(v, include_none=include_none) for v in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted(dataclass_to_dict(v, include_none=include_none) for v in obj)
    if isinstance(obj, dict):
        return {str(k): dataclass_to_dict(v, include_none=include_none) for k, v in obj.items() if include_none or v is not None}
    return obj


def dataclass_from_dict(cls: type[T], data: Mapping[str, Any] | None) -> T:
    if data is None:
        data = {}
    return _convert_value(cls, data)


def _convert_value(tp: Any, value: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(tp)
    args = get_args(tp)

    if origin in (Union, UnionType):
        non_none = [arg for arg in args if arg is not type(None)]
        if value is None:
            return None
        for arg in non_none:
            try:
                return _convert_value(arg, value)
            except Exception:
                continue
        return value

    if is_dataclass(tp):
        if not isinstance(value, Mapping):
            raise TypeError(f"Expected mapping for {tp}, got {type(value).__name__}")
        hints = get_type_hints(tp)
        kwargs: dict[str, Any] = {}
        for f in fields(tp):
            if f.name in value:
                kwargs[f.name] = _convert_value(hints.get(f.name, Any), value[f.name])
            elif f.default is not MISSING:
                kwargs[f.name] = f.default
            elif f.default_factory is not MISSING:  # type: ignore[comparison-overlap]
                kwargs[f.name] = f.default_factory()  # type: ignore[misc]
            else:
                missing = default_missing_value(hints.get(f.name, Any))
                if missing is MISSING:
                    raise ValueError(f"Missing required field {tp.__name__}.{f.name}")
                kwargs[f.name] = missing
        return tp(**kwargs)

    if origin in (list, Sequence):
        inner = args[0] if args else Any
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        converted = []
        for item in value:
            try:
                converted.append(_convert_value(inner, item))
            except Exception:
                # Drop incomplete list entries rather than failing the entire extraction.
                continue
        return converted

    if origin in (dict, Mapping):
        if not isinstance(value, Mapping):
            return {}
        key_type = args[0] if args else str
        value_type = args[1] if len(args) > 1 else Any
        return {_convert_value(key_type, k): _convert_value(value_type, v) for k, v in value.items()}

    if isinstance(tp, type) and issubclass_safe(tp, Enum):
        return enum_from_value(tp, value)
    if tp is date:
        parsed = parse_date_fuzzy(str(value))
        if parsed is None:
            raise ValueError(f"Cannot parse date: {value}")
        return parsed
    if tp is bool:
        return as_bool(value)
    if tp is int:
        parsed = as_int(value)
        if parsed is None:
            raise ValueError(f"Cannot parse int: {value}")
        return parsed
    if tp is float:
        parsed = as_float(value)
        if parsed is None:
            raise ValueError(f"Cannot parse float: {value}")
        return parsed
    if tp is str:
        return str(value)
    return value


def default_missing_value(tp: Any) -> Any:
    origin = get_origin(tp)
    args = get_args(tp)
    if origin in (Union, UnionType) and type(None) in args:
        return None
    if origin in (list, Sequence):
        return []
    if origin in (dict, Mapping):
        return {}
    if tp in {str, int, float, bool}:
        return None
    return MISSING


def dataclass_json_schema(cls: type[Any]) -> dict[str, Any]:
    return _schema_for_type(cls)


def _schema_for_type(tp: Any) -> dict[str, Any]:
    origin = get_origin(tp)
    args = get_args(tp)

    if origin in (Union, UnionType):
        non_none = [arg for arg in args if arg is not type(None)]
        schemas = [_schema_for_type(arg) for arg in non_none]
        if type(None) in args:
            schemas.append({"type": "null"})
        return {"anyOf": schemas} if len(schemas) > 1 else schemas[0]

    if is_dataclass(tp):
        hints = get_type_hints(tp)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for f in fields(tp):
            properties[f.name] = _schema_for_type(hints.get(f.name, Any))
            if f.default is MISSING and f.default_factory is MISSING:  # type: ignore[comparison-overlap]
                required.append(f.name)
        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        if tp.__doc__:
            schema["description"] = normalize_whitespace(tp.__doc__)
        return schema

    if origin in (list, Sequence):
        inner = args[0] if args else Any
        return {"type": "array", "items": _schema_for_type(inner)}
    if origin in (dict, Mapping):
        value_type = args[1] if len(args) > 1 else Any
        return {"type": "object", "additionalProperties": _schema_for_type(value_type)}

    if tp is Any:
        return {}
    if isinstance(tp, type) and issubclass_safe(tp, Enum):
        return {"type": "string", "enum": [member.value for member in tp]}
    if tp is str:
        return {"type": "string"}
    if tp is bool:
        return {"type": "boolean"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is date:
        return {"type": "string", "format": "date"}
    return {}


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------


def merge_application_seed(target: ds.DistilledSpiritsApplication, seed: ds.DistilledSpiritsApplication) -> None:
    """Fill fields from deterministic seed when the LLM left them blank."""

    if not target.application_id:
        target.application_id = seed.application_id
    merge_dataclass_blank_fields(target.identity, seed.identity)
    merge_dataclass_blank_fields(target.alcohol, seed.alcohol)
    merge_dataclass_blank_fields(target.net_contents, seed.net_contents)
    if not target.country_of_origin:
        target.country_of_origin = seed.country_of_origin
    if not target.responsible_parties:
        target.responsible_parties = seed.responsible_parties
    target.extra_application_facts = {**seed.extra_application_facts, **target.extra_application_facts}


def merge_label_seed(target: ds.DistilledSpiritsLabelExtraction, seed: ds.DistilledSpiritsLabelExtraction) -> None:
    """Fill extracted fields from deterministic seed when the LLM left them blank."""

    for f in fields(ds.DistilledSpiritsLabelExtraction):
        if f.name in {"extra_extracted_facts"}:
            continue
        target_value = getattr(target, f.name)
        seed_value = getattr(seed, f.name)
        if is_blank_value(target_value) and not is_blank_value(seed_value):
            setattr(target, f.name, seed_value)
        elif is_dataclass(target_value) and is_dataclass(seed_value):
            merge_dataclass_blank_fields(target_value, seed_value)
    target.extra_extracted_facts = {**seed.extra_extracted_facts, **target.extra_extracted_facts}


def merge_dataclass_blank_fields(target: Any, seed: Any) -> None:
    if not (is_dataclass(target) and is_dataclass(seed)):
        return
    for f in fields(target):
        target_value = getattr(target, f.name)
        seed_value = getattr(seed, f.name)
        if is_blank_value(target_value) and not is_blank_value(seed_value):
            setattr(target, f.name, seed_value)
        elif is_dataclass(target_value) and is_dataclass(seed_value):
            merge_dataclass_blank_fields(target_value, seed_value)
        elif isinstance(target_value, dict) and isinstance(seed_value, dict):
            setattr(target, f.name, {**seed_value, **target_value})


def is_blank_value(value: Any) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    if value == [] or value == {}:
        return True
    if isinstance(value, ds.ExtractedText):
        return not value.is_present
    return False


# ---------------------------------------------------------------------------
# Checks for downstream validator/bootstrap UI
# ---------------------------------------------------------------------------


def populate_precomputed_checks(review: ds.DistilledSpiritsLabelReviewInput) -> None:
    app = review.application
    label = review.label
    checks: dict[str, ds.Check] = {}

    checks["DS-LABEL-001.brand_name_present"] = ds.Check.from_bool(
        label.brand_name.value.is_present,
        reason="Label brand name text was extracted." if label.brand_name.value.is_present else "No brand name text was extracted.",
        rule_ids=["DS-LABEL-001"],
    )
    if app.identity.brand_name:
        checks["brand_name_matches_application"] = ds.Check.from_bool(
            label.brand_name.matches_application_brand_name,
            reason=f"Application brand is {app.identity.brand_name!r}.",
            rule_ids=["DS-LABEL-001"],
        )

    checks["DS-LABEL-010.class_type_present"] = ds.Check.from_bool(
        label.class_type.statement.is_present,
        rule_ids=["DS-LABEL-010"],
    )
    if app.identity.class_type_designation:
        checks["DS-LABEL-011.class_type_matches_application"] = ds.Check.from_bool(
            label.class_type.matches_application_class_type,
            rule_ids=["DS-LABEL-011"],
        )

    checks["DS-LABEL-080.alcohol_content_present"] = ds.Check.from_bool(
        label.alcohol_content.abv_percent is not None,
        rule_ids=["DS-LABEL-080"],
    )
    checks["DS-LABEL-081.alcohol_content_uses_abv_phrase"] = ds.Check.from_bool(
        label.alcohol_content.has_percent_alcohol_by_volume_phrase,
        rule_ids=["DS-LABEL-081"],
    )
    if app.alcohol.abv_percent is not None:
        checks["DS-LABEL-083.abv_matches_application"] = ds.Check.from_bool(
            label.alcohol_content.matches_application_abv_with_tolerance,
            rule_ids=["DS-LABEL-083", "DS-LABEL-084", "DS-LABEL-085", "DS-LABEL-086"],
        )

    checks["DS-LABEL-070.net_contents_present"] = ds.Check.from_bool(
        label.net_contents.net_contents_ml is not None,
        rule_ids=["DS-LABEL-070"],
    )
    checks["DS-LABEL-072.net_contents_standard_fill"] = ds.Check.from_bool(
        label.net_contents.is_metric_standard_of_fill,
        rule_ids=["DS-LABEL-072", "DS-LABEL-073", "DS-LABEL-074"],
    )
    if app.net_contents.net_contents_ml is not None:
        checks["net_contents_matches_application"] = ds.Check.from_bool(
            label.net_contents.matches_application_net_contents,
            rule_ids=["DS-LABEL-070"],
        )

    imported = app.import_status != ds.ImportStatus.DOMESTIC
    checks["DS-LABEL-040_050_052.responsible_party_present"] = ds.Check.from_bool(
        bool(label.responsible_party_statements),
        rule_ids=["DS-LABEL-040"] if not imported else ["DS-LABEL-050", "DS-LABEL-052"],
    )
    if imported:
        checks["DS-LABEL-060.country_of_origin_present"] = ds.Check.from_bool(
            label.country_of_origin.statement.is_present,
            rule_ids=["DS-LABEL-060"],
        )
        if app.country_of_origin:
            checks["DS-LABEL-061.country_of_origin_matches_application"] = ds.Check.from_bool(
                label.country_of_origin.matches_application_country,
                rule_ids=["DS-LABEL-061"],
            )

    if app.disclosures.contains_fdc_yellow_5:
        checks["DS-LABEL-120.fdc_yellow_5_disclosed"] = ds.Check.from_bool(
            label.fdc_yellow_5_disclosure.contains_required_phrase,
            rule_ids=["DS-LABEL-120"],
        )
    if app.disclosures.contains_saccharin:
        checks["DS-LABEL-130.saccharin_disclosed"] = ds.Check.from_bool(
            label.saccharin_disclosure.exact_required_text_present,
            rule_ids=["DS-LABEL-130"],
        )
    sulfite_required = app.disclosures.contains_sulfites_at_declaration_threshold
    if sulfite_required is True:
        checks["DS-LABEL-140.sulfites_disclosed"] = ds.Check.from_bool(
            any(
                value is True
                for value in [
                    label.sulfite_declaration.contains_sulfites_phrase_present,
                    label.sulfite_declaration.contains_sulfiting_agents_phrase_present,
                    label.sulfite_declaration.specific_sulfiting_agents_declared,
                ]
            ),
            rule_ids=["DS-LABEL-140"],
        )

    if app.commodity_statement.group == ds.CommodityStatementGroup.GROUP_1_PERCENT_AND_COMMODITY:
        checks["DS-LABEL-150.commodity_statement_group1_present"] = ds.Check.from_bool(
            label.commodity_statement.group1_percent_and_commodity_present,
            rule_ids=["DS-LABEL-150", "DS-LABEL-152"],
        )
    elif app.commodity_statement.group == ds.CommodityStatementGroup.GROUP_2_COMMODITY_ONLY:
        checks["DS-LABEL-153.commodity_statement_group2_present"] = ds.Check.from_bool(
            label.commodity_statement.group2_distilled_from_commodity_present,
            rule_ids=["DS-LABEL-153", "DS-LABEL-155"],
        )

    age_required = app.age.age_statement_required_by_age()
    if age_required is not None:
        checks["DS-LABEL-160_161_162.age_statement_present_when_required"] = ds.Check.from_bool(
            label.age_statement.required_age_statement_present,
            rule_ids=["DS-LABEL-160", "DS-LABEL-161", "DS-LABEL-162"],
        )
    if label.age_statement.age_is_not_overstated is not None:
        checks["DS-LABEL-172.age_not_overstated"] = ds.Check.from_bool(
            label.age_statement.age_is_not_overstated,
            rule_ids=["DS-LABEL-172"],
        )

    if app.state_of_distillation.state_of_distillation_statement_required is True:
        checks["DS-LABEL-180.state_of_distillation_present"] = ds.Check.from_bool(
            label.state_of_distillation.statement.is_present,
            rule_ids=["DS-LABEL-180"],
        )

    # Warning is always extracted from text, but full compliance can remain UNKNOWN when text-only OCR
    # cannot prove boldness/continuous paragraph.  The exact text and all-caps header checks are still useful.
    warning_required = app.sale.for_sale_or_distribution_in_us and app.sale.intended_for_human_consumption
    if app.alcohol.abv_percent is not None:
        warning_required = warning_required and app.alcohol.abv_percent >= 0.5
    checks["DS-LABEL-190.government_warning_present"] = ds.Check.from_bool(
        label.government_warning.full_text.is_present or label.government_warning.header_text.is_present,
        rule_ids=["DS-LABEL-190"],
    ) if warning_required else ds.Check(state=ds.ComplianceState.NOT_APPLICABLE, rule_ids=["DS-LABEL-190"])
    checks["DS-LABEL-191.government_warning_exact_text"] = ds.Check.from_bool(
        label.government_warning.exact_required_text_present,
        rule_ids=["DS-LABEL-191"],
    )
    checks["DS-LABEL-192.government_warning_header_caps"] = ds.Check.from_bool(
        label.government_warning.header_is_exact_all_caps,
        rule_ids=["DS-LABEL-192"],
    )
    checks["government_warning_text_only_compliance"] = ds.Check.from_bool(
        label.government_warning.government_warning_compliant,
        reason="Unknown means exact text may be present but text-only OCR cannot prove bold/non-bold/continuous paragraph style.",
        rule_ids=["DS-LABEL-190", "DS-LABEL-191", "DS-LABEL-192", "DS-LABEL-193", "DS-LABEL-194"],
    )

    rule_results = build_rule_result_dicts(review)
    for check in checks.values():
        for rule_id in check.rule_ids:
            if rule_id in rule_results.rule_passes:
                check.reason = rule_results.rule_passes[rule_id]
                break
            elif rule_id in rule_results.rule_fails:
                check.reason = rule_results.rule_fails[rule_id]
                break
            elif rule_id in rule_results.rule_unknown:
                check.reason = rule_results.rule_unknown[rule_id]["reason"]
                break

    review.checks.update(checks)


# ---------------------------------------------------------------------------
# Generic normalization / matching helpers
# ---------------------------------------------------------------------------


def normalize_whitespace(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()


def normalize_for_match(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return normalize_whitespace(value)


def find_phrase_case_insensitive(text: str, phrase: str) -> str | None:
    if not phrase:
        return None
    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(0)
    normalized_text = normalize_for_match(text)
    normalized_phrase = normalize_for_match(phrase)
    if normalized_phrase and normalized_phrase in normalized_text:
        return phrase
    return None


def contains_normalized_text(haystack: str, needle: str, *, case_sensitive: bool) -> bool:
    hay = normalize_whitespace(haystack)
    ned = normalize_whitespace(needle)
    if not case_sensitive:
        hay = hay.upper()
        ned = ned.upper()
    return ned in hay


def names_match(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    l_norm = normalize_for_match(left)
    r_norm = normalize_for_match(right)
    if not l_norm or not r_norm:
        return None
    return l_norm == r_norm or l_norm in r_norm or r_norm in l_norm


def class_type_match(label_value: str | None, app_value: str | None) -> bool | None:
    if not label_value or not app_value:
        return None
    label_norm = normalize_for_match(label_value).replace("whiskey", "whisky")
    app_norm = normalize_for_match(app_value).replace("whiskey", "whisky")
    if label_norm == app_norm:
        return True
    # Application code may be extra noisy, e.g. "OTHER RUM GOLD USB".  Matching the core class/type
    # token is useful but not conclusive for specialty products, so return True only for clear core terms.
    core_terms = ["rum", "vodka", "gin", "brandy", "tequila", "mezcal", "whisky", "liqueur", "cordial"]
    shared = [term for term in core_terms if term in label_norm and term in app_norm]
    return bool(shared)


def country_match(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    return normalize_for_match(canonical_country_name(left)) == normalize_for_match(canonical_country_name(right))


def commodity_match(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    l_norm = normalize_for_match(left)
    r_norm = normalize_for_match(right)
    if l_norm == r_norm:
        return True
    # Rules allow specific commodity or general class in some cases.
    general_classes = {
        "corn": "grain",
        "rye": "grain",
        "wheat": "grain",
        "barley": "grain",
        "malted barley": "grain",
        "grape": "fruit",
        "apple": "fruit",
        "pear": "fruit",
    }
    return general_classes.get(l_norm) == r_norm or general_classes.get(r_norm) == l_norm


def state_match(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    return normalize_for_match(left) == normalize_for_match(right)


def canonical_country_name(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = normalize_whitespace(value).strip(" .,:;-")
    normalized = normalize_for_match(cleaned)
    aliases = {
        "usa": "United States",
        "us": "United States",
        "u s a": "United States",
        "united states": "United States",
        "united states of america": "United States",
        "brasil": "Brazil",
        "uk": "United Kingdom",
        "u k": "United Kingdom",
        "england": "United Kingdom",
        "scotland": "United Kingdom",
    }
    return aliases.get(normalized, cleaned.title() if cleaned.isupper() else cleaned)


def is_us_country(value: str | None) -> bool:
    if not value:
        return False
    return normalize_for_match(value) in _US_COUNTRY_VALUES or canonical_country_name(value) == "United States"


def empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = clean_application_value(value)
    return value or None


def parse_date_fuzzy(value: str | None) -> date | None:
    if not value:
        return None
    value = normalize_whitespace(value)
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y", "%B %Y", "%b %Y"]:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def as_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "t", "yes", "y", "1", "pass"}:
        return True
    if normalized in {"false", "f", "no", "n", "0", "fail"}:
        return False
    return None


def enum_from_value(enum_cls: type[Enum], value: Any) -> Enum:
    if isinstance(value, enum_cls):
        return value
    text = str(value)
    for member in enum_cls:
        if text == member.value or text == member.name or text.lower() == member.value.lower() or text.upper() == member.name:
            return member
    raise ValueError(f"Unknown {enum_cls.__name__} value: {value}")


def issubclass_safe(value: Any, class_or_tuple: Any) -> bool:
    try:
        return issubclass(value, class_or_tuple)
    except TypeError:
        return False


# ---------------------------------------------------------------------------
# Convenience CLI for local smoke tests
# ---------------------------------------------------------------------------


def load_ocr_blocks_from_text_file(path: str | Path) -> list[OcrTextBlock]:
    """Treat each non-empty line in a text file as an OCR block."""

    text = Path(path).read_text(encoding="utf-8")
    return [OcrTextBlock(text=line, block_id=str(i), reading_order=i) for i, line in enumerate(text.splitlines()) if line.strip()]


def dump_review_input_json(review: ds.DistilledSpiritsLabelReviewInput, path: str | Path) -> None:
    Path(path).write_text(json.dumps(dataclass_to_dict(review, include_none=True), indent=2, sort_keys=True), encoding="utf-8")
