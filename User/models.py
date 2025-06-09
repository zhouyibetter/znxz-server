from pydantic import BaseModel
from cryptography.fernet import Fernet


class RegisterInfo(BaseModel):
    """
    User registration information.
    """
    email: str
    password: str


class LoginInfo(BaseModel):
    """
    User login information.
    """
    email: str
    password: str


class Result(BaseModel):
    """
    Result of an operation.
    """
    code: int
    token: str
    