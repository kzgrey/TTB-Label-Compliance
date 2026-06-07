
EXTRACT_FULL_FIELDS_PROMPT = """
You extract alcoholic beverage label facts directly from the provided image. There is no OCR text input; read the image manually.

Rules:
- Use only text visibly present in the image.
- Copy text exactly as shown: casing, punctuation, symbols, abbreviations, spelling, and visible typos.
- Do not infer, correct, normalize, translate, summarize, or compute missing values.
- Do not derive ABV from proof or proof from ABV unless both are explicitly printed.
- A value may concatenate multiple visible spans or lines in reading order. Join spans with one space.
- If text is absent, cut off, unreadable, or uncertain, use null.
- Return JSON only.

Output exactly:

{
  "Label": {
    "BrandName": null,
    "ClassTypeDesignation": null,
    "ABV": null,
    "NetContents": null,
    "BottlerProducerNameAddr": null,
    "ImportOrigin": null,
    "FancifulName": null,
    "WhiskyDesignation": null,
    "Proof": null,
    "ColoringMaterialDisclosure": null,
    "ForeignComponentPercentagesAndOrigins": null,
    "RuleSpecificFact": null,
    "PercentageAndName": null,
    "ContainerEmbossedText": null,
    "GovernmentWarningText": null,
    "ContainerOrLabelCoding": null
  },
  "Evidence": {
    "BrandName": [],
    "ClassTypeDesignation": [],
    "ABV": [],
    "NetContents": [],
    "BottlerProducerNameAddr": [],
    "ImportOrigin": [],
    "FancifulName": [],
    "WhiskyDesignation": [],
    "Proof": [],
    "ColoringMaterialDisclosure": [],
    "ForeignComponentPercentagesAndOrigins": [],
    "RuleSpecificFact": [],
    "PercentageAndName": [],
    "ContainerEmbossedText": [],
    "GovernmentWarningText": [],
    "ContainerOrLabelCoding": []
  }
}

For each non-null Label field, Evidence[field] must contain one or more entries:

{
  "visibleText": "exact copied visible text",
  "location": "brief image location, e.g. top center, lower left, back label middle"
}

The Label[field] value must equal the Evidence[field].visibleText values joined with one space.

Field meanings:
- BrandName: brand name.
- ClassTypeDesignation: product class/type/statement of identity.
- ABV: alcohol-content statement.
- NetContents: net-contents statement.
- BottlerProducerNameAddr: bottler, producer, brewer, distiller, importer, or responsible party name/address.
- ImportOrigin: explicit country-of-origin or imported-from statement.
- FancifulName: product name separate from brand and class/type.
- WhiskyDesignation: whisky-specific designation, such as bourbon, rye, straight whisky, blended whisky, single malt.
- Proof: printed proof statement.
- ColoringMaterialDisclosure: coloring, caramel color, artificial color, or certified color disclosure.
- ForeignComponentPercentagesAndOrigins: foreign component percentage/origin statement.
- RuleSpecificFact: relevant label text that fits no other field.
- PercentageAndName: percentage/name listing for blended components.
- ContainerEmbossedText: embossed, blown, branded, molded, etched, or container-formed text.
- GovernmentWarningText: complete government warning statement.
- ContainerOrLabelCoding: printed/stamped/coded lot, batch, date, or production marking.

Selection rules:
- Prefer the most complete explicit visible statement.
- If one span fits multiple fields, use the most specific field.
- Do not use an address alone as ImportOrigin unless the image explicitly states origin/import language.
- Do not put GovernmentWarningText in RuleSpecificFact.
"""



NORMALIZE_TEXTBLOCKS_PROMPT = """You are an information extraction normalizer.

Input will contain OCR text blocks extracted from an alcoholic beverage product label.

Your task is to normalize the input text blocks into JSON.

Critical rules:

1. Do not invent values.
2. Do not correct spelling, punctuation, capitalization, OCR mistakes, or grammar.
3. Every extracted value must be copied from the input text exactly, preserving casing, punctuation, spacing within the copied text, abbreviations, and typos.
4. A field may be constructed by concatenating multiple copied text spans from one or more input blocks.
5. If concatenating multiple spans, preserve each copied span exactly and join spans with a single space unless the original text already contains the needed separator.
6. If a value cannot be directly supported by copied source text, output null.
7. Do not infer values from general knowledge.
8. Do not normalize units. For example, keep "Alc. 6.8% by Vol." exactly as written.
9. Do not translate.
10. Do not summarize.
11. Do not include explanatory text outside JSON.

Input format:

The input is a list of text blocks. Treat the blocks as ordered from top to bottom, left to right unless coordinates are provided.

Output format:

Return only valid JSON with this structure:

{
"Label": {
"BrandName": null,
"ClassTypeDesignation": null,
"ABV": null,
"NetContents": null,
"BottlerProducerNameAddr": null,
"ImportOrigin": null,
"FancifulName": null,
"WhiskyDesignation": null,
"Proof": null,
"ColoringMaterialDisclosure": null,
"ForeignComponentPercentagesAndOrigins": null,
"RuleSpecificFact": null,
"PercentageAndName": null,
"ContainerEmbossedText": null,
"GovernmentWarningText": null,
"ContainerOrLabelCoding": null
},
"Sources": {
"BrandName": [],
"ClassTypeDesignation": [],
"ABV": [],
"NetContents": [],
"BottlerProducerNameAddr": [],
"ImportOrigin": [],
"FancifulName": [],
"WhiskyDesignation": [],
"Proof": [],
"ColoringMaterialDisclosure": [],
"ForeignComponentPercentagesAndOrigins": [],
"RuleSpecificFact": [],
"PercentageAndName": [],
"ContainerEmbossedText": [],
"GovernmentWarningText": [],
"ContainerOrLabelCoding": []
}
}

For each non-null Label field, Sources[fieldName] must contain one or more source entries:

{
"blockIndex": 0,
"exactText": "copied text exactly as it appeared in the input block"
}

If a field is null, its Sources entry must be an empty array.

Field definitions:

BrandName:
The brand name text appearing on the label.

ClassTypeDesignation:
The product class, type, or statement of identity, such as beer, ale, wine, whisky, vodka, distilled spirits, lager, stout, etc.

ABV:
The alcohol-content statement, including surrounding wording if present.

NetContents:
The net-contents statement, including volume and unit wording.

BottlerProducerNameAddr:
The name and address statement for the bottler, producer, brewer, distiller, importer, or similar responsible party.

ImportOrigin:
The country-of-origin or imported-from statement.

FancifulName:
A product name that is separate from the brand name and class/type designation.

WhiskyDesignation:
A whisky-specific designation, such as bourbon, rye, straight whisky, blended whisky, single malt, etc., only if explicitly present.

Proof:
The proof statement, only if explicitly present.

ColoringMaterialDisclosure:
A disclosure about coloring materials, artificial color, caramel color, certified color, or similar, only if explicitly present.

ForeignComponentPercentagesAndOrigins:
A statement describing percentages or origins of foreign components, only if explicitly present.

RuleSpecificFact:
Any rule-relevant label text that does not fit another normalized field.

PercentageAndName:
A percentage/name listing for blended components, only if explicitly present.

ContainerEmbossedText:
Text described or marked as embossed, blown, branded, molded, etched, or otherwise physically part of the container.

GovernmentWarningText:
The complete government warning statement, including the words "GOVERNMENT WARNING" and all warning text that follows, if present.

ContainerOrLabelCoding:
Printed, stamped, coded, lot, batch, date, or production marking on the label or container.

Extraction guidance:

* Prefer the most complete contiguous statement for each field.
* If the same information appears multiple times, use the clearest and most complete version.
* If a text block contains multiple facts, extract only the relevant exact span for each field.
* If a fact is split across blocks, concatenate the exact spans in reading order.
* If a field might fit more than one category, choose the most specific field.
* GovernmentWarningText should not be placed in RuleSpecificFact if GovernmentWarningText is available.
* ABV and Proof are separate fields. Do not put proof into ABV unless the text explicitly combines them.
* NetContents should contain only the net contents statement, not unrelated keg size options unless those are the only available net contents text.
* BottlerProducerNameAddr should include both name and address if both are present.
* ImportOrigin should only be populated when the label explicitly states an import origin or country of origin.

Return JSON only.
"""

NORMALIZE_TEXTBLOCKS_PROMPT2 = """Extract label facts from OCR text blocks into JSON.

Rules:
- Copy text exactly from the input: same casing, punctuation, spelling, OCR typos, and symbols.
- Do not infer, rewrite, normalize units, fix typos, translate, or summarize.
- Every non-null value must be supported by one or more exact source spans from the input.
- Values may concatenate multiple source spans in reading order. Join spans with one space.
- If no exact source text supports a field, use null.
- Return JSON only.

Input: ordered OCR text blocks. Use 0-based blockIndex.

Output exactly:

{
  "Label": {
    "BrandName": null,
    "ClassTypeDesignation": null,
    "ABV": null,
    "NetContents": null,
    "BottlerProducerNameAddr": null,
    "ImportOrigin": null,
    "FancifulName": null,
    "WhiskyDesignation": null,
    "Proof": null,
    "ColoringMaterialDisclosure": null,
    "ForeignComponentPercentagesAndOrigins": null,
    "RuleSpecificFact": null,
    "PercentageAndName": null,
    "ContainerEmbossedText": null,
    "GovernmentWarningText": null,
    "GovernmentWarningHeaderText": null,
    "ContainerOrLabelCoding": null
  },
  "Sources": {
    "BrandName": [],
    "ClassTypeDesignation": [],
    "ABV": [],
    "NetContents": [],
    "BottlerProducerNameAddr": [],
    "ImportOrigin": [],
    "FancifulName": [],
    "WhiskyDesignation": [],
    "Proof": [],
    "ColoringMaterialDisclosure": [],
    "ForeignComponentPercentagesAndOrigins": [],
    "RuleSpecificFact": [],
    "PercentageAndName": [],
    "ContainerEmbossedText": [],
    "GovernmentWarningText": [],
    "GovernmentWarningHeaderText": [],
    "ContainerOrLabelCoding": []
  }
}

For each non-null Label field, Sources[field] must be:
[
  {"blockIndex": 0, "exactText": "exact copied source span"}
]

The Label[field] value must equal its Sources[field].exactText values joined with one space.

Field meanings:
- BrandName: brand name.
- ClassTypeDesignation: Distilled Spirits, Beer, Wine, Other
- ABV: alcohol-content statement.
- NetContents: net-contents statement.
- BottlerProducerNameAddr: bottler, producer, brewer, distiller, importer, or responsible party name/address.
- ImportOrigin: country-of-origin or imported-from statement.
- FancifulName: product name separate from brand and class/type.
- WhiskyDesignation: whisky-specific designation.
- Proof: proof statement.
- ColoringMaterialDisclosure: coloring/caramel/artificial/certified color disclosure.
- ForeignComponentPercentagesAndOrigins: foreign component percentage/origin statement.
- RuleSpecificFact: relevant label text that fits no other field.
- PercentageAndName: percentage/name listing for blended components.
- ContainerEmbossedText: embossed, blown, branded, molded, etched, or container-formed text.
- GovernmentWarningText: complete government warning statement.
- GovernmentWarningHeaderText: exact text of the government warning header (e.g. 'GOVERNMENT WARNING:').
- ContainerOrLabelCoding: printed/stamped/coded lot, batch, date, or production marking.

Selection rules:
- Prefer the most complete explicit statement.
- If one text span fits multiple fields, use the most specific field.
- Keep ABV and Proof separate unless the source text explicitly combines them.
- Do not put GovernmentWarningText in RuleSpecificFact."""

