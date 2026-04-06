from pydantic import BaseModel

class Contact(BaseModel):
    email: str
    first_name: str
    second_name: str
    address: str

