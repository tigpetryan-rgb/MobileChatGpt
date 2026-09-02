from pydantic import BaseModel, Field


class DevicePairingCreate(BaseModel):
    ttl_seconds: int = Field(default=600, ge=60, le=3600)


class DeviceRegister(BaseModel):
    pairing_code: str = Field(min_length=16, max_length=256)
    name: str = Field(min_length=1, max_length=200)
    platform: str = Field(default="android", min_length=1, max_length=32)


class DeviceCommandEnqueue(BaseModel):
    project_id: str
    task_id: str | None = None
    agent_run_id: str | None = None
    tool_name: str = Field(min_length=1, max_length=120)
    payload: dict
    idempotency_key: str = Field(min_length=1, max_length=200)
    external_side_effect: bool = False
    approval_id: str | None = None


class DeviceCommandClaim(BaseModel):
    lease_seconds: int = Field(default=120, ge=30, le=900)


class DeviceCommandHeartbeat(BaseModel):
    lease_seconds: int = Field(default=120, ge=30, le=900)


class DeviceCommandComplete(BaseModel):
    result: dict


class DeviceCommandFail(BaseModel):
    error: str = Field(min_length=1, max_length=4000)
