# =============================================================================
# app/utils/hash.py  —  PASSWORD HASHING
# =============================================================================
# NEVER store plain-text passwords in a database.
# Instead, store a one-way cryptographic hash.  When a user logs in, hash the
# submitted password and compare hashes — never the original password.
#
# LEARNING CONCEPT ► bcrypt
#   bcrypt is a password-hashing algorithm designed to be SLOW ON PURPOSE.
#   This makes brute-force and rainbow-table attacks impractical.
#
#   Key properties:
#   1. SALT: a random value mixed into the hash so identical passwords produce
#      different hashes.  Stored inside the hash string itself.
#   2. COST FACTOR (rounds): controls how slow the hashing is.  Default is 12.
#      Doubling rounds doubles the time (and attacker's work).
#   3. ONE-WAY: you cannot reverse a bcrypt hash to get the original password.
#
# LEARNING EXAMPLE ► what a bcrypt hash looks like:
#   plain:   "mypassword123"
#   hashed:  "$2b$12$Ei/9...longstring..."
#              ^^  ^^ ^^
#              |   |  |-- the salt + hash (22+31 chars)
#              |   |-- cost factor (2^12 = 4096 iterations)
#              |-- bcrypt version
# =============================================================================

import bcrypt


# =============================================================================
# hash_password
# =============================================================================
# 1. `bcrypt.gensalt()` generates a random salt (16 bytes by default).
# 2. `bcrypt.hashpw(password_bytes, salt)` applies bcrypt to produce the hash.
# 3. `.decode('utf-8')` converts the bytes result to a string for database storage.
#
# LEARNING NOTE ► .encode('utf-8')
#   bcrypt operates on bytes, not strings.
#   `plain.encode('utf-8')` converts a Python string → bytes.
#   `hashed_bytes.decode('utf-8')` converts bytes back → string.
# =============================================================================
def hash_password(plain: str) -> str:
    """Hash a plain-text password. Mirrors hashPassword() in utils/hash.ts."""
    salt = bcrypt.gensalt()                              # random salt
    hashed_bytes = bcrypt.hashpw(plain.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')                  # store as string in DB


# =============================================================================
# compare_passwords
# =============================================================================
# `bcrypt.checkpw` hashes the plain-text password with the SAME SALT that is
# embedded in `hashed`, then compares the result in constant time.
#
# "Constant time" means the comparison takes the same time whether it matches
# or not — this prevents timing attacks that could reveal the hash.
#
# RETURNS: True if the password matches the hash, False otherwise.
#
# LEARNING EXAMPLE ► usage in login:
#   stored_hash = user.password                   # from database
#   if not compare_passwords(body.password, stored_hash):
#       raise AppError("Invalid credentials", 401)
# =============================================================================
def compare_passwords(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a hash. Mirrors comparePasswords()."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
