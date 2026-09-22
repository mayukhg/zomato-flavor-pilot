"""Cart management endpoints."""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from backend.app.schemas import (
    BuildCartRequest,
    CartResponse,
    ApproveCartRequest,
    ApproveCartResponse,
    CartItem,
)
from backend.db import get_session
from backend.db.models import Cart

router = APIRouter()


@router.post("/build", response_model=CartResponse)
async def build_cart(request: BuildCartRequest):
    """
    Build and stage a cart for user approval.
    
    Creates a cart with selected items, applies promo codes,
    and calculates final pricing with fees.
    """
    # Generate cart ID
    cart_id = f"cart_{uuid.uuid4().hex[:16]}"
    
    # Calculate totals
    subtotal = sum(item.price_inr * item.quantity for item in request.items)
    
    # Apply promo discount (mock calculation)
    discount = 0.0
    if request.promo_code:
        if request.promo_code == "CBUSER":
            discount = 240.0
        elif request.promo_code == "HEALTH20":
            discount = subtotal * 0.2
    
    delivery_fee = 29.0
    platform_fee = 49.0
    total = subtotal - discount + delivery_fee + platform_fee
    
    # Persist cart to database
    async with get_session() as session:
        cart = Cart(
            cart_id=cart_id,
            session_id=request.session_id,
            restaurant_id=request.restaurant_id,
            restaurant_name="Mock Restaurant",  # Would be fetched from MCP
            items=[item.model_dump() for item in request.items],
            delivery_address=request.delivery_address.model_dump(),
            subtotal_inr=subtotal,
            discount_inr=discount,
            delivery_fee_inr=delivery_fee,
            platform_fee_inr=platform_fee,
            total_inr=total,
            promo_code=request.promo_code,
            status="staged",
        )
        session.add(cart)
        await session.commit()
        await session.refresh(cart)
        
        return CartResponse(
            cart_id=cart.cart_id,
            session_id=cart.session_id,
            restaurant_id=cart.restaurant_id,
            restaurant_name=cart.restaurant_name,
            items=[CartItem(**item) for item in cart.items],
            subtotal_inr=cart.subtotal_inr,
            discount_inr=cart.discount_inr,
            delivery_fee_inr=cart.delivery_fee_inr,
            platform_fee_inr=cart.platform_fee_inr,
            total_inr=cart.total_inr,
            promo_code=cart.promo_code,
            status=cart.status,
            created_at=cart.created_at,
        )


@router.post("/approve", response_model=ApproveCartResponse)
async def approve_cart(request: ApproveCartRequest):
    """
    Approve a staged cart for order placement.
    
    Requires explicit human approval and allergen safety confirmation.
    """
    async with get_session() as session:
        # Fetch cart
        result = await session.execute(
            select(Cart).where(Cart.cart_id == request.cart_id)
        )
        cart = result.scalar_one_or_none()
        
        if not cart:
            raise HTTPException(status_code=404, detail=f"Cart {request.cart_id} not found")
        
        if cart.status != "staged":
            raise HTTPException(
                status_code=400,
                detail=f"Cart cannot be approved from status '{cart.status}'"
            )
        
        # Check allergen confirmation
        if not request.allergen_confirmed:
            raise HTTPException(
                status_code=400,
                detail="Allergen safety must be confirmed before approval"
            )
        
        # Update cart status
        cart.status = "approved"
        cart.approved_at = datetime.utcnow()
        await session.commit()
        
        # Generate order token (would integrate with Zomato payment API)
        order_token = f"order_token_{uuid.uuid4().hex[:24]}"
        
        return ApproveCartResponse(
            cart_id=cart.cart_id,
            status="approved",
            message="Cart approved and staged. Payment locked in prototype mode.",
            order_token=order_token,
        )


@router.get("/{cart_id}", response_model=CartResponse)
async def get_cart(cart_id: str):
    """Retrieve cart details by ID."""
    async with get_session() as session:
        result = await session.execute(
            select(Cart).where(Cart.cart_id == cart_id)
        )
        cart = result.scalar_one_or_none()
        
        if not cart:
            raise HTTPException(status_code=404, detail=f"Cart {cart_id} not found")
        
        return CartResponse(
            cart_id=cart.cart_id,
            session_id=cart.session_id,
            restaurant_id=cart.restaurant_id,
            restaurant_name=cart.restaurant_name,
            items=[CartItem(**item) for item in cart.items],
            subtotal_inr=cart.subtotal_inr,
            discount_inr=cart.discount_inr,
            delivery_fee_inr=cart.delivery_fee_inr,
            platform_fee_inr=cart.platform_fee_inr,
            total_inr=cart.total_inr,
            promo_code=cart.promo_code,
            status=cart.status,
            created_at=cart.created_at,
        )
