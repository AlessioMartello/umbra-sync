from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Contact(BaseModel):
    email_address: EmailStr
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    monday_id: Optional[str] = None
    address: Optional[str] = None
    job_title: Optional[str] = None
    website: Optional[str] = None
