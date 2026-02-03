import httpx
from src.config import settings
from src.logs.middleware import logger


async def notify_new_order(order) -> None:
    """Send a Telegram message to staff chat about a new order."""
    token = settings.TG_BOT_TOKEN
    chat_id = settings.TG_STAFF_CHAT_ID
    if not token or not chat_id:
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

    try:
            response = httpx.post(
                url=f"https://api.telegram.org/bot{token}/sendMessage",
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
            )
            if response.status_code != 200:
                logger.warning(f"[TG] Failed to send notification: {response.status_code} {response.text}")
    except Exception as e:
        logger.warning(f"[TG] Error sending notification: {e}")
