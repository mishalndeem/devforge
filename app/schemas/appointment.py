from pydantic import BaseModel
from pydantic import EmailStr
from typing import Optional


class AppointmentRequest(BaseModel):

    name: str

    phone: str

    email: Optional[EmailStr] = None

    preferred_date: Optional[str] = None

    message: Optional[str] = None