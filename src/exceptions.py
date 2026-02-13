"""Domain exceptions for ParfumShop.

Service layer raises these instead of HTTPException (which belongs only in routers).
FastAPI exception handlers in main.py convert them to HTTP responses.
"""


class ShopError(Exception):
    """Base class for all domain exceptions."""


class NotFoundError(ShopError):
    """Raised when a requested resource does not exist."""


class BusinessRuleError(ShopError):
    """Raised when a business rule is violated (e.g. minimum order amount not met,
    bundle no longer available, invalid coupon state).

    Replaces bare ValueError in the service layer.
    """


class AuthorizationError(ShopError):
    """Raised when the current user lacks permission for the requested action."""


class DuplicateResourceError(ShopError):
    """Raised when a unique constraint would be violated (e.g. duplicate email, slug)."""
