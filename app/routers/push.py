
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, PushSubscription
from ..schemas import StandardResponse, PushSubscribeInput, PushUnsubscribeInput
from ..utils.security import verify_api_key, get_current_user
from ..utils.timezone import now_tz
from ..utils.rate_limiter import limiter
from ..adapters.notification import NotificationPayload, get_notification_service
from ..bot.locales import get_text
import logging
import uuid

router = APIRouter(prefix="/api/v1/push", tags=["web push"])
logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    return str(uuid.uuid4())


def create_standard_response(status, message, data=None, request_id=None):
    return StandardResponse(
        status=status,
        message=message,
        data=data,
        request_id=request_id or generate_request_id()
    )


@router.post("/subscribe", response_model=StandardResponse)
@limiter.limit("10/hour")
async def subscribe(
    request: Request,
    subscription: PushSubscribeInput,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Register (or reactivate) a Web Push subscription — upsert by endpoint."""
    request_id = generate_request_id()

    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == subscription.endpoint
    ).first()

    if existing:
        if existing.user_id != current_user.id:
            # Push endpoints are device+origin scoped; another account on
            # this browser profile owned it before. Reassigning silently
            # would leak notifications across accounts — reject.
            raise HTTPException(
                status_code=409,
                detail="Subscription endpoint is registered to another account"
            )
        existing.p256dh = subscription.keys.p256dh
        existing.auth = subscription.keys.auth
        existing.user_agent = request.headers.get("user-agent", "")[:500]
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        sub_id = existing.id
        message = "Subscription reactivated"
    else:
        new_sub = PushSubscription(
            user_id=current_user.id,
            endpoint=subscription.endpoint,
            p256dh=subscription.keys.p256dh,
            auth=subscription.keys.auth,
            user_agent=request.headers.get("user-agent", "")[:500],
            created_at=now_tz(),
            is_active=True,
        )
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)
        sub_id = new_sub.id
        message = "Subscription created"

    logger.info(
        f"Push subscription upsert for user {current_user.id} "
        f"(id={sub_id}) - Request ID: {request_id}")

    return create_standard_response(
        status="success",
        message=message,
        data={"id": sub_id},
        request_id=request_id
    )


@router.delete("/subscribe", response_model=StandardResponse)
async def unsubscribe(
    request: Request,
    body: PushUnsubscribeInput,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Deactivate a Web Push subscription owned by the current user."""
    request_id = generate_request_id()

    sub = db.query(PushSubscription).filter(
        PushSubscription.endpoint == body.endpoint,
        PushSubscription.user_id == current_user.id
    ).first()

    if sub:
        sub.is_active = False
        db.commit()

    # Idempotent: unknown endpoint is still a successful unsubscribe.
    return create_standard_response(
        status="success",
        message="Unsubscribed",
        data={"success": True},
        request_id=request_id
    )


@router.post("/test", response_model=StandardResponse)
@limiter.limit("5/minute")
async def send_test_notification(
    request: Request,
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Send a test notification to the current user's own push devices."""
    request_id = generate_request_id()

    service = get_notification_service()
    channel = service.channels.get("web_push")
    if channel is None:
        raise HTTPException(
            status_code=503, detail="Web push is not configured on this server")

    lang = current_user.language or "th"
    payload = NotificationPayload(
        title=get_text("push_test_title", lang),
        body=get_text("push_test_body", lang),
        tag="bp-test",
        url="/settings",
    )

    # Test targets web_push directly (the point is verifying this device),
    # bypassing preference fallback. Body contains no health data, so D4
    # does not apply.
    result = await channel.send(db, current_user, payload)

    logger.info(
        f"Push test for user {current_user.id}: "
        f"{'delivered' if result.success else result.error} "
        f"- Request ID: {request_id}")

    return create_standard_response(
        status="success" if result.success else "error",
        message="Test notification sent" if result.success
        else f"Delivery failed: {result.error}",
        data={"delivered": result.success},
        request_id=request_id
    )
