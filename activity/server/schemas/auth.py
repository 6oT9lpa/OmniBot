from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    code: str = Field(min_length=1, max_length=2048)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
