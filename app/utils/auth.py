"""JWT 认证工具"""
import hashlib
import os
import time
from typing import Optional
from dataclasses import dataclass

import jwt

SECRET_KEY = os.getenv("JWT_SECRET", hashlib.sha256(os.urandom(32)).hexdigest())
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

USER_STORE: dict[str, dict] = {}
USER_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "users.json")


def _load_users():
    global USER_STORE
    try:
        import json
        with open(USER_FILE, encoding="utf-8") as f:
            USER_STORE = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        USER_STORE = {"admin": {"username": "admin", "password": _hash_pw("admin123"), "role": "admin"}}


def _save_users():
    import json
    os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(USER_STORE, f, ensure_ascii=False, indent=2)


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


_load_users()


@dataclass
class TokenPayload:
    username: str
    role: str
    exp: int


def create_token(username: str, role: str) -> str:
    payload = {"username": username, "role": role, "exp": int(time.time()) + TOKEN_EXPIRE_HOURS * 3600}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(username=payload["username"], role=payload["role"], exp=payload["exp"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def authenticate(username: str, password: str) -> Optional[str]:
    user = USER_STORE.get(username)
    if not user or user.get("password") != _hash_pw(password):
        return None
    return create_token(username, user.get("role", "operator"))


def register_user(username: str, password: str, role: str = "operator") -> bool:
    if username in USER_STORE:
        return False
    USER_STORE[username] = {"username": username, "password": _hash_pw(password), "role": role}
    _save_users()
    return True


def get_user(username: str) -> Optional[dict]:
    user = USER_STORE.get(username)
    if user:
        return {"username": user["username"], "role": user["role"]}
    return None
