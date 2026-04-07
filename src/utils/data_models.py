from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class Contact(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    address: Optional[str] = None

