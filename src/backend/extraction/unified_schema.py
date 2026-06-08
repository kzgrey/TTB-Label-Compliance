from typing import Optional
from pydantic import BaseModel, ConfigDict

class LabelData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    BrandName: Optional[str] = None
    ClassTypeDesignation: Optional[str] = None
    ABV: Optional[str] = None
    NetContents: Optional[str] = None
    BottlerProducerNameAddr: Optional[str] = None
    ImportOrigin: Optional[str] = None
    FancifulName: Optional[str] = None
    WhiskyDesignation: Optional[str] = None
    Proof: Optional[str] = None
    ColoringMaterialDisclosure: Optional[str] = None
    ForeignComponentPercentagesAndOrigins: Optional[str] = None
    RuleSpecificFact: Optional[str] = None
    PercentageAndName: Optional[str] = None
    ContainerEmbossedText: Optional[str] = None
    GovernmentWarningText: Optional[str] = None
    GovernmentWarningHeaderText: Optional[str] = None
    ContainerOrLabelCoding: Optional[str] = None
