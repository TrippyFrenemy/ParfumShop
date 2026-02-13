from celery import shared_task
from sqlalchemy import text

from src.tasks.db import engine
from src.tasks.notifications import send_telegram_message


@shared_task
def send_periodic_reports_task() -> None:
    """Generate and send a bi-monthly sales report to the staff chat."""
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*)                AS total_orders,
                        COALESCE(SUM(total), 0) AS total_revenue,
                        COUNT(*) FILTER (WHERE status = 'paid')    AS paid_count,
                        COUNT(*) FILTER (WHERE status = 'shipped') AS shipped_count
                    FROM orders
                    WHERE created_at >= CURRENT_DATE - INTERVAL '15 days'
                    """
                )
            ).fetchone()

        total_orders = row[0] if row else 0
        total_revenue = row[1] if row else 0
        paid_count = row[2] if row else 0
        shipped_count = row[3] if row else 0

        message = (
            f"\U0001f4cb <b>Звіт за останні 15 днів</b>\n\n"
            f"\U0001f4e6 Замовлень: {total_orders}\n"
            f"\U0001f4b3 Оплачених: {paid_count}\n"
            f"\U0001f69a Відправлених: {shipped_count}\n"
            f"\U0001f4b0 Виручка: {total_revenue} грн"
        )
        send_telegram_message(settings.TG_STAFF_CHAT_ID, message)
        print(f"[REPORTING] Periodic report sent: {total_orders} orders, {total_revenue} UAH")
    except Exception as exc:
        print(f"[REPORTING] Failed to send periodic report: {exc}")
