"""Feedback module."""

# Lazy import to avoid circular imports during model loading
def get_router():
    from .router import router
    return router

__all__ = ["get_router"]
