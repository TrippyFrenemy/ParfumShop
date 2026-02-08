import html
import httpx
from src.config import settings
from src.logs.middleware import logger


def _esc(v) -> str:
    # Экранируем все динамические строки, чтобы не ломать HTML в Telegram
    return html.escape("" if v is None else str(v), quote=False)


async def notify_new_order(order) -> None:
    """Send a Telegram message to staff chat about a new order."""
    if not settings.TG_BOT_TOKEN or not settings.TG_CHAT_ID:
        logger.warning("[TG] Telegram bot token or chat ID not configured")
        return

    lines: list[str] = []

    # Заголовок
    lines.append(f"🛒 <b>Нове замовлення №{_esc(order.order_number)}</b>")

    # Клиент
    lines.append("")
    lines.append(f"👤 <b>{_esc(order.full_name)}</b>")
    lines.append(f"📞 {_esc(order.phone)}")
    if order.email:
        lines.append(f"📧 {_esc(order.email)}")

    # Доставка
    lines.append("")
    lines.append(f"📦 <b>Доставка:</b> {_esc(order.delivery_method_ua)}")
    if order.city:
        lines.append(f"🏙 {_esc(order.city)}")
    if order.warehouse:
        lines.append(f"🏢 {_esc(order.warehouse)}")
    if order.address:
        lines.append(f"📍 {_esc(order.address)}")

    # Товары
    lines.append("")
    lines.append("<b>Товари:</b>")
    for item in order.items:
        lines.append(
            f"• {_esc(item.product_name)} ×{_esc(item.quantity)} — <b>{_esc(item.total)} грн</b>"
        )

    # Итоги
    lines.append("")
    lines.append(f"💰 <b>Всього:</b> <b>{_esc(order.total)} грн</b>")

    if order.comment:
        lines.append("")
        lines.append(f"💬 <b>Коментар:</b> {_esc(order.comment)}")

    # Ссылка в админку (нормальный кликабельный anchor)
    base = (settings.URL or "").rstrip("/")
    admin_url = f"{base}/admin/orders/{order.id}"
    lines.append("")
    lines.append(f'🔗 <a href="{html.escape(admin_url, quote=True)}">Переглянути в адмін-панелі</a>')

    text = "\n".join(lines)

    url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url=url, json=payload, timeout=10.0)
            if response.status_code != 200:
                logger.warning(f"[TG] Failed to send notification: {response.status_code} {response.text}")
    except Exception as e:
        logger.warning(f"[TG] Error sending notification: {e}")
