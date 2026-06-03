"""Password hashing and verification utilities."""

from passlib.context import CryptContext

# Bcrypt context setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The unhashed password.
        hashed_password: The bcrypt hashed password.
        
    Returns:
        True if valid, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a bcrypt hash from a plain password.
    
    Args:
        password: The unhashed password.
        
    Returns:
        The bcrypt hashed password.
    """
    return pwd_context.hash(password)
