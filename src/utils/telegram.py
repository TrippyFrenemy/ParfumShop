import httpx
from src.config import settings
from src.logs.middleware import logger


async def notify_new_order(order) -> None:
    """Send a Telegram message to staff chat about a new order."""
    if not settings.TG_BOT_TOKEN or not settings.TG_CHAT_ID:
        logger.warning("[TG] Telegram bot token or chat ID not configured")
        return

    items_text = ""
    for item in order.items:
        items_text += f"  - {item.product_name} x{item.quantity} = {item.total} грн\n"

    text = (
        f"🛒 <b>Нове замовлення #{order.order_number}</b>\n\n"
        f"👤 {order.full_name}\n"
        f"📞 {order.phone}\n"
    )
    if order.email:
        text += f"📧 {order.email}\n"
    text += (
        f"\n📦 {order.delivery_method_ua}\n"
    )
    if order.city:
        text += f"🏙 {order.city}\n"
    if order.warehouse:
        text += f"🏢 {order.warehouse}\n"
    if order.address:
        text += f"📍 {order.address}\n"
    text += (
        f"\n<b>Товари:</b>\n{items_text}"
        f"\n💰 <b>Всього: {order.total} грн</b>\n"
    )
    if order.comment:
        text += f"\n💬 {order.comment}\n"

    # Admin panel link — relative, will be prefixed by staff
    text += f"\n🔗 <a href='{settings.URL}/admin/orders/{order.id}'>Переглянути в адмiн-панелi</a>"

    url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url=url, json=payload, timeout=10.0)
            if response.status_code != 200:
                logger.warning(f"[TG] Failed to send notification: {response.status_code} {response.text}")
    except Exception as e:
        logger.warning(f"[TG] Error sending notification: {e}")
