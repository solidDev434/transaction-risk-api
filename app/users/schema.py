import uuid
from .model import UserBase


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: uuid.UUID
