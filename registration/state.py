from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegistrationState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = Field(default=None, description="User's full name")
    email: Optional[EmailStr] = Field(default=None, description="User email")
    phone: Optional[str] = Field(default=None, description="10 digit phone number")
    dob: Optional[str] = Field(default=None, description="DD-MM-YYYY")
    pan: Optional[str] = Field(default=None, description="Permanent Account Number")

    validation_errors: Dict[str, str] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)