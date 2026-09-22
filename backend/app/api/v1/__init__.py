"""API v1 routes initialization."""
from fastapi import APIRouter

from backend.app.api.v1 import search, trajectory, cart, evals

api_router = APIRouter()

api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(trajectory.router, prefix="/agent", tags=["agent"])
api_router.include_router(cart.router, prefix="/cart", tags=["cart"])
api_router.include_router(evals.router, prefix="/evals", tags=["evals"])
