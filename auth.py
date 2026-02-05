# Simple token-based auth system
VALID_TOKENS = {
    "reports_tool": "token123",
    "analytics_tool": "token456",
    # add more tool tokens here
}

ADMIN_TOKEN = "admin-secret-123"

def authenticate(token: str) -> bool:
    """Return True if token is valid"""
    return token in VALID_TOKENS.values()

def verify_admin(token: str) -> bool:
    """Return True if token is the admin token"""
    return token == ADMIN_TOKEN
