from pydantic import BaseModel
from app.modules.users.schemas import UserResponse

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    user: UserResponse
    token: Token
