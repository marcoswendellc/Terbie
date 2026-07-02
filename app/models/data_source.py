from pydantic import BaseModel, ConfigDict, Field


class GoogleSheetsLoadRequest(BaseModel):
    spreadsheet_id: str | None = Field(default=None, min_length=1)
    sheet_names: list[str] | None = None

    model_config = ConfigDict(frozen=True)
