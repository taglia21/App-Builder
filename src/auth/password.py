"""
LaunchForge Password Security Module

Secure password hashing using bcrypt with strength validation.
"""

import re
from typing import List, Tuple

import bcrypt


class PasswordStrengthError(Exception):
    """Raised when password doesn't meet strength requirements."""

    def __init__(self, message: str, errors: List[str]):
        super().__init__(message)
        self.errors = errors


# Password strength configuration
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
BCRYPT_ROUNDS = 12  # Cost factor for bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Bcrypt hash of the password
    """
    # Encode password to bytes
    password_bytes = password.encode('utf-8')

    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        hashed: Bcrypt hash to verify against

    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password meets strength requirements.

    Requirements:
    - Minimum 8 characters
    - Maximum 128 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (optional but recommended)

    Args:
        password: Password to validate

    Returns:
        Tuple[bool, List[str]]: (is_valid, list of error messages)
    """
    errors = []

    # Length checks
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")

    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append(f"Password must not exceed {MAX_PASSWORD_LENGTH} characters")

    # Character class checks
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")

    # Optional but tracked: special characters
    bool(re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~]', password))

    is_valid = len(errors) == 0

    return is_valid, errors


def check_password_strength(password: str) -> None:
    """
    Check password strength and raise exception if invalid.

    Args:
        password: Password to check

    Raises:
        PasswordStrengthError: If password doesn't meet requirements
    """
    is_valid, errors = validate_password_strength(password)
    if not is_valid:
        raise PasswordStrengthError(
            "Password does not meet strength requirements",
            errors
        )


def get_password_strength_score(password: str) -> dict:
    """
    Calculate a password strength score with feedback.

    Args:
        password: Password to score

    Returns:
        dict: Score and feedback information
    """
    score = 0
    feedback = []

    # Length scoring
    length = len(password)
    if length >= 8:
        score += 1
    if length >= 12:
        score += 1
    if length >= 16:
        score += 1

    # Character diversity
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1

    # Common patterns to avoid (decreases score)
    common_patterns = [
        r'123', r'abc', r'qwerty', r'password', r'admin',
        r'letmein', r'welcome', r'monkey', r'dragon'
    ]
    for pattern in common_patterns:
        if re.search(pattern, password.lower()):
            score -= 1
            feedback.append(f"Avoid common patterns like '{pattern}'")

    # Normalize score
    score = max(0, min(score, 7))

    # Strength label
    if score <= 2:
        strength = "weak"
    elif score <= 4:
        strength = "fair"
    elif score <= 5:
        strength = "good"
    else:
        strength = "strong"

    return {
        "score": score,
        "max_score": 7,
        "strength": strength,
        "feedback": feedback,
        "is_valid": score >= 3,
    }
