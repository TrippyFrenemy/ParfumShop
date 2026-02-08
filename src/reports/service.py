"""Business logic for reports module."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Tuple
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.reports.schemas import ReportFilters, PeriodType
from src.orders.models import Order, OrderStatus, OrderItem
from src.reports.queries import (
    get_discount_analysis,
    get_sales_trend,
    get_top_products,
    get_dead_stock,
    get_aov_trend,
    get_orders_by_city,
    get_customer_stats,
    get_top_customers,
    get_customers_by_city,
    get_delivery_by_method,
    get_orders_without_ttn
)


def calculate_date_range(filters: ReportFilters) -> Tuple[date, date]:
    """Calculate date range based on filters."""
    if filters.period == PeriodType.CUSTOM:
        if filters.date_from and filters.date_to:
            return filters.date_from, filters.date_to
        # Fallback to month if custom dates not provided
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date

    end_date = date.today()

    if filters.period == PeriodType.TODAY:
        start_date = end_date
    elif filters.period == PeriodType.WEEK:
        start_date = end_date - timedelta(days=7)
    elif filters.period == PeriodType.MONTH:
        start_date = end_date - timedelta(days=30)
    elif filters.period == PeriodType.YEAR:
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)

    return start_date, end_date


async def get_overview_stats(session: AsyncSession, filters: ReportFilters) -> Dict[str, Any]:
    """Get overview statistics for dashboard."""
    start_date, end_date = calculate_date_range(filters)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Current period stats
    revenue_stmt = select(func.sum(Order.total)).where(
        and_(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
        )
    )
    total_revenue = (await session.execute(revenue_stmt)).scalar() or Decimal('0')

    orders_count_stmt = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
        )
    )
    orders_count = (await session.execute(orders_count_stmt)).scalar() or 0

    # Average Order Value
    aov = float(total_revenue / orders_count) if orders_count > 0 else 0

    # Pending orders (status = CREATED)
    pending_stmt = select(func.count(Order.id)).where(
        Order.status == OrderStatus.CREATED
    )
    pending_orders = (await session.execute(pending_stmt)).scalar() or 0

    # Calculate changes vs previous period if requested
    revenue_change = None
    orders_change = None
    aov_change = None

    if filters.compare_previous:
        # Calculate previous period date range
        period_days = (end_date - start_date).days
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_days)
        prev_start_dt = datetime.combine(prev_start_date, datetime.min.time())
        prev_end_dt = datetime.combine(prev_end_date, datetime.max.time())

        # Previous period revenue
        prev_revenue_stmt = select(func.sum(Order.total)).where(
            and_(
                Order.created_at >= prev_start_dt,
                Order.created_at <= prev_end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        prev_revenue = (await session.execute(prev_revenue_stmt)).scalar() or Decimal('0')

        # Previous period orders count
        prev_orders_stmt = select(func.count(Order.id)).where(
            and_(
                Order.created_at >= prev_start_dt,
                Order.created_at <= prev_end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        prev_orders = (await session.execute(prev_orders_stmt)).scalar() or 0

        # Calculate percentage changes
        if prev_revenue > 0:
            revenue_change = float(((total_revenue - prev_revenue) / prev_revenue) * 100)
        if prev_orders > 0:
            orders_change = float(((orders_count - prev_orders) / prev_orders) * 100)
        if prev_orders > 0:
            prev_aov = float(prev_revenue / prev_orders)
            if prev_aov > 0:
                aov_change = ((aov - prev_aov) / prev_aov) * 100

    return {
        "total_revenue": float(total_revenue),
        "orders_count": orders_count,
        "aov": aov,
        "pending_orders": pending_orders,
        "revenue_change": revenue_change,
        "orders_change": orders_change,
        "aov_change": aov_change,
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
    }


async def get_sales_report(session: AsyncSession, filters: ReportFilters) -> Dict[str, Any]:
    """Get detailed sales report with discounts and trends."""
    start_date, end_date = calculate_date_range(filters)

    # Get discount analysis
    discount_data = await get_discount_analysis(session, start_date, end_date)

    # Get sales trend for daily breakdown
    trend_data = await get_sales_trend(session, start_date, end_date, granularity='day')

    return {
        "total_revenue": discount_data['total_revenue'],
        "total_subtotal": discount_data['total_subtotal'],
        "total_discounts": discount_data['total_discounts'],
        "total_orders": discount_data['total_orders'],
        "orders_with_discount": discount_data['orders_with_discount'],
        "orders_with_coupon": discount_data['orders_with_coupon'],
        "avg_discount_pct": discount_data['avg_discount_pct'],
        "discount_rate": discount_data['discount_rate'],
        "daily_breakdown": trend_data,
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
    }


async def get_products_report(session: AsyncSession, filters: ReportFilters) -> Dict[str, Any]:
    """Get detailed products performance report."""
    start_date, end_date = calculate_date_range(filters)

    # Get top products by revenue
    top_by_revenue = await get_top_products(session, start_date, end_date, limit=10, order_by='revenue')

    # Get top products by quantity
    top_by_quantity = await get_top_products(session, start_date, end_date, limit=10, order_by='quantity')

    # Get dead stock (products not sold in 30+ days)
    dead_stock = await get_dead_stock(session, days_threshold=30)

    return {
        "top_by_revenue": top_by_revenue,
        "top_by_quantity": top_by_quantity,
        "dead_stock": dead_stock,
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
    }


async def get_orders_report(session: AsyncSession, filters: ReportFilters) -> Dict[str, Any]:
    """Get detailed orders analytics report."""
    start_date, end_date = calculate_date_range(filters)
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    # Get AOV and average items per order
    aov_stmt = select(
        func.avg(Order.total).label('aov'),
        func.avg(
            select(func.sum(OrderItem.quantity))
            .where(OrderItem.order_id == Order.id)
            .correlate(Order)
            .scalar_subquery()
        ).label('avg_items')
    ).where(
        and_(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
        )
    )

    result = await session.execute(aov_stmt)
    row = result.one()
    aov = float(row.aov or Decimal('0'))
    avg_items = float(row.avg_items or Decimal('0'))

    # Get orders count
    count_stmt = select(func.count(Order.id)).where(
        and_(
            Order.created_at >= start_dt,
            Order.created_at <= end_dt,
            Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
        )
    )
    orders_count = (await session.execute(count_stmt)).scalar() or 0

    # Get AOV trend
    aov_trend = await get_aov_trend(session, start_date, end_date, granularity='day')

    # Get top cities
    top_cities = await get_orders_by_city(session, start_date, end_date, limit=10)

    return {
        "aov": aov,
        "avg_items": avg_items,
        "orders_count": orders_count,
        "aov_trend": aov_trend,
        "top_cities": top_cities,
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
    }


async def get_customers_report(session: AsyncSession, filters: ReportFilters) -> Dict[str, Any]:
    """Get customers insights report."""
    start_date, end_date = calculate_date_range(filters)

    customer_stats = await get_customer_stats(session, start_date, end_date)
    top_customers = await get_top_customers(session, start_date, end_date, limit=10)
    top_cities = await get_customers_by_city(session, start_date, end_date, limit=10)

    return {
        "total_customers": customer_stats['total_customers'],
        "new_customers": customer_stats['new_customers'],
        "repeat_customers": customer_stats['repeat_customers'],
        "top_customers": top_customers,
        "top_cities": top_cities,
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
    }


async def get_financial_report(session: AsyncSession, filters: ReportFilters) -> Dict[str, Any]:
    """Get financial summary report."""
    start_date, end_date = calculate_date_range(filters)

    # Reuse discount analysis
    financial_data = await get_discount_analysis(session, start_date, end_date)

    return {
        "total_revenue": financial_data['total_revenue'],
        "total_subtotal": financial_data['total_subtotal'],
        "total_discounts": financial_data['total_discounts'],
        "avg_discount_pct": financial_data['avg_discount_pct'],
        "net_revenue": financial_data['total_revenue'],
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
    }


async def get_delivery_report(session: AsyncSession, filters: ReportFilters) -> Dict[str, Any]:
    """Get delivery analytics report."""
    start_date, end_date = calculate_date_range(filters)

    delivery_methods = await get_delivery_by_method(session, start_date, end_date)
    top_cities = await get_orders_by_city(session, start_date, end_date, limit=10)
    orders_without_ttn = await get_orders_without_ttn(session, start_date, end_date, limit=20)

    return {
        "delivery_methods": delivery_methods,
        "top_cities": top_cities,
        "orders_without_ttn": orders_without_ttn,
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
    }
