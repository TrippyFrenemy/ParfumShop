import httpx
from celery import shared_task
from sqlalchemy import text

from src.config import settings
from src.tasks.db import engine


def send_telegram_message(chat_id: str, message_text: str) -> bool:
    """Send a message to a Telegram chat via Bot API.

    Returns True on success, False otherwise.
    """
    url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML",
    }
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        if response.status_code == 200:
            return True
        print(f"[NOTIFY] Telegram API error: {response.status_code} {response.text}")
        return False
    except Exception as exc:
        print(f"[NOTIFY] Failed to send Telegram message: {exc}")
        return False


@shared_task
def send_new_order_notification(
    order_number: str,
    full_name: str,
    total: str,
    items_count: int,
) -> None:
    """Notify staff about a newly created order."""
    message = (
        f"\U0001f6d2 <b>Нове замовлення #{order_number}</b>\n"
        f"\U0001f464 {full_name}\n"
        f"\U0001f4b0 {total} грн\n"
        f"\U0001f4e6 Товарів: {items_count}"
    )
    send_telegram_message(settings.TG_STAFF_CHAT_ID, message)


@shared_task
def send_order_paid_notification(order_number: str, total: str) -> None:
    """Notify staff that an order has been paid."""
    message = (
        f"\u2705 <b>Замовлення #{order_number} оплачено</b>\n"
        f"\U0001f4b0 {total} грн"
    )
    send_telegram_message(settings.TG_STAFF_CHAT_ID, message)


@shared_task
def send_daily_order_summary() -> None:
    """Send a summary of today's orders to the staff chat."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*)            AS total_orders,
                        COALESCE(SUM(total), 0) AS total_revenue,
                        COUNT(*) FILTER (WHERE status = 'paid')    AS paid_count,
                        COUNT(*) FILTER (WHERE status = 'created') AS new_count
                    FROM orders
                    WHERE created_at::date = CURRENT_DATE
                    """
                )
            ).fetchone()

        total_orders = row[0] if row else 0
        total_revenue = row[1] if row else 0
        paid_count = row[2] if row else 0
        new_count = row[3] if row else 0

        message = (
            f"\U0001f4ca <b>Денний звіт замовлень</b>\n\n"
            f"\U0001f4e6 Всього замовлень: {total_orders}\n"
            f"\U0001f195 Нових: {new_count}\n"
            f"\U0001f4b3 Оплачених: {paid_count}\n"
            f"\U0001f4b0 Загальна сума: {total_revenue} грн"
        )
        send_telegram_message(settings.TG_STAFF_CHAT_ID, message)
        print(f"[NOTIFY] Daily order summary sent: {total_orders} orders, {total_revenue} UAH")
    except Exception as exc:
        print(f"[NOTIFY] Failed to build daily order summary: {exc}")


@shared_task
def send_weekly_performance_summary() -> None:
    """Send a weekly performance summary to the staff chat (last 7 days)."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*)            AS total_orders,
                        COALESCE(SUM(total), 0) AS total_revenue,
                        COUNT(*) FILTER (WHERE status = 'paid')      AS paid_count,
                        COUNT(*) FILTER (WHERE status = 'shipped')   AS shipped_count,
                        COUNT(DISTINCT user_id)                      AS unique_customers
                    FROM orders
                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                    """
                )
            ).fetchone()

        total_orders = row[0] if row else 0
        total_revenue = row[1] if row else 0
        paid_count = row[2] if row else 0
        shipped_count = row[3] if row else 0
        unique_customers = row[4] if row else 0

        avg_check = round(float(total_revenue) / total_orders, 2) if total_orders > 0 else 0

        message = (
            f"\U0001f4c8 <b>Тижневий звіт</b>\n\n"
            f"\U0001f4e6 Замовлень: {total_orders}\n"
            f"\U0001f4b3 Оплачених: {paid_count}\n"
            f"\U0001f69a Відправлених: {shipped_count}\n"
            f"\U0001f465 Унікальних клієнтів: {unique_customers}\n"
            f"\U0001f4b0 Виручка: {total_revenue} грн\n"
            f"\U0001f9fe Середній чек: {avg_check} грн"
        )
        send_telegram_message(settings.TG_STAFF_CHAT_ID, message)
        print(
            f"[NOTIFY] Weekly summary sent: {total_orders} orders, "
            f"{total_revenue} UAH, {unique_customers} customers"
        )
    except Exception as exc:
        print(f"[NOTIFY] Failed to build weekly performance summary: {exc}")
