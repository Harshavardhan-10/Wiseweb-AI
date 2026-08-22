from pydantic import BaseModel, ConfigDict, Field


class ArchitectureNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    node_type: str
    name: str
    label: str | None
    metadata: dict | None = Field(default=None, validation_alias="meta")


class ArchitectureEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_node_id: int
    target_node_id: int
    relationship: str
    metadata: dict | None = Field(default=None, validation_alias="meta")


class ArchitectureResponse(BaseModel):
    nodes: list[ArchitectureNodeResponse]
    edges: list[ArchitectureEdgeResponse]
