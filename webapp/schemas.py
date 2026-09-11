from pydantic import BaseModel


class LoginBody(BaseModel):
    phone: str
    password: str


class RegionBody(BaseModel):
    region: str
    enabled: bool


class ThreatBody(BaseModel):
    key: str
    enabled: bool


class ThreatKeywordBody(BaseModel):
    key: str
    keyword: str


class ChannelBody(BaseModel):
    key: str
    enabled: bool


class ChannelAddBody(BaseModel):
    input: str
