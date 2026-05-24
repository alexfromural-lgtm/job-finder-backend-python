import bcrypt

def hash_password(plain: str) -> str:
    """Hash a plain-text password. Mirrors hashPassword() in utils/hash.ts."""
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(plain.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')


def compare_passwords(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a hash. Mirrors comparePasswords()."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
