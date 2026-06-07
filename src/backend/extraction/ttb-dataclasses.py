@dataclass
class Application:
    # Product brand name from the application.
    BrandName: str

    # Product class/type designation from the application.
    ClassTypeDesignation: str

    # Known alcohol content from the application.
    ABV: str

    # Known container size from the application.
    NetContents: str

    # Known bottler/producer/importer name and address from the application.
    BottlerProducerNameAddr: str

    # Country of origin for imported products.
    ImportOrigin: Optional[str] = None

    # Actual operation address when different from principal place of business.
    ActualOperationAddress: Optional[str] = None

    # Predominant flavor for flavored products.
    PredominantFlavor: Optional[str] = None

    # Recognized cocktail name, if applicable.
    CocktailName: Optional[str] = None

    # Distilled spirits components used in a cocktail/product.
    DistilledSpiritsComponents: Optional[list[str]] = None

    # Foreign component percentages and origins for blended/import-related products.
    ForeignComponentPercentagesAndOrigins: Optional[str] = None

@dataclass
class Label:
    # Brand name text extracted from the label.
    BrandName: Optional[str] = None

    # Class/type designation text extracted from the label.
    ClassTypeDesignation: Optional[str] = None

    # Alcohol-content statement extracted from the label.
    ABV: Optional[str] = None

    # Net-contents statement extracted from the label.
    NetContents: Optional[str] = None

    # Bottler/producer/importer name and address statement extracted from the label.
    BottlerProducerNameAddr: Optional[str] = None

    # Country-of-origin statement extracted from the label.
    ImportOrigin: Optional[str] = None

    # Fanciful product name extracted from the label.
    FancifulName: Optional[str] = None

    # Whisky-specific designation extracted from the label.
    WhiskyDesignation: Optional[str] = None

    # Proof statement extracted from the label, if present.
    Proof: Optional[str] = None

    # Coloring-material disclosure extracted from the label.
    ColoringMaterialDisclosure: Optional[str] = None

    # Foreign component percentage/origin statement extracted from the label.
    ForeignComponentPercentagesAndOrigins: Optional[str] = None

    # Rule-specific extracted text that does not fit a normalized field.
    RuleSpecificFact: Optional[str] = None

    # Percentage/name listing for blended components.
    PercentageAndName: Optional[str] = None

    # Text embossed, blown, or branded into the container.
    ContainerEmbossedText: Optional[str] = None

    # Printed/coded marking on the label or container.
    ContainerOrLabelCoding: Optional[str] = None