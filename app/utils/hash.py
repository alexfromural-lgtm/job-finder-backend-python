from passlib.context import CryptContext

# bcrypt context — mirrors the Node.js `bcrypt` library
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plain-text password. Mirrors hashPassword() in utils/hash.ts."""
    return _pwd_context.hash(plain)


def compare_passwords(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a hash. Mirrors comparePasswords()."""
    return _pwd_context.verify(plain, hashed)
