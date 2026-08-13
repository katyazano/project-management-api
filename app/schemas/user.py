import re
from typing import Self
from pydantic import BaseModel, ConfigDict, model_validator, field_validator, EmailStr


# User schemas

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    username: str
    email: EmailStr
    password: str
    repeat_password: str

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', value):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', value):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', value):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]/~`]', value):
            raise ValueError('Password must contain at least one special character')
        return value

    @model_validator(mode='after')
    def check_passwords_match(self) -> Self:
        if self.password != self.repeat_password:
            raise ValueError('Passwords do not match')
        return self

class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Token schemas

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None