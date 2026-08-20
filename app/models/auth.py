from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

    model_config = ConfigDict(frozen=True)


class LoginResponse(BaseModel):
    authenticated: bool
    cd_usuario: str | None = None
    nm_usuario: str | None = None
    access_token: str | None = None
    expires_in: int | None = None

    model_config = ConfigDict(frozen=True)
