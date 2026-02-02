from typing import Optional
from pydantic import BaseModel

class Usercreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: Optional[int] = None
    username: Optional[str] = None

    model_config = {"from_attributes": True}

class UserLogin(BaseModel):
    username: str
    password: str