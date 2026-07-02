from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    app: str

    model_config = ConfigDict(frozen=True)
