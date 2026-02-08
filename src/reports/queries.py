"""SQL queries for reports analytics."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.orders.models import Order, OrderItem, OrderStatus
from src.products.models import Product, Category


async def get_sales_trend(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    granularity: str = 'day'
) -> List[Dict[str, Any]]:
    """
    Get sales trend over time.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date
        granularity: 'day', 'week', or 'month'

    Returns:
        List of dictionaries with date, revenue, orders_count
    """
    # Convert dates to datetime
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    # Determine truncation function based on granularity
    if granularity == 'day':
        trunc = func.date_trunc('day', Order.created_at)
    elif granularity == 'week':
        trunc = func.date_trunc('week', Order.created_at)
    else:
        trunc = func.date_trunc('month', Order.created_at)

    # Build query
    stmt = (
        select(
            trunc.label('period'),
            func.sum(Order.total).label('revenue'),
            func.count(Order.id).label('orders_count')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        .group_by('period')
        .order_by('period')
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'date': row.period.strftime('%Y-%m-%d'),
            'revenue': float(row.revenue or Decimal('0')),
            'orders_count': row.orders_count or 0
        }
        for row in rows
    ]


async def get_top_products(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    limit: int = 5,
    order_by: str = 'revenue'
) -> List[Dict[str, Any]]:
    """
    Get top products by revenue or quantity.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date
        limit: Number of products to return
        order_by: 'revenue' or 'quantity'

    Returns:
        List of dictionaries with product_name, brand, revenue, quantity
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            OrderItem.product_name,
            Product.brand.label('product_brand'),
            func.sum(OrderItem.total).label('revenue'),
            func.sum(OrderItem.quantity).label('quantity')
        )
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .outerjoin(Product, Product.id == OrderItem.product_id)
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        .group_by(OrderItem.product_name, Product.brand)
    )

    if order_by == 'quantity':
        stmt = stmt.order_by(func.sum(OrderItem.quantity).desc())
    else:
        stmt = stmt.order_by(func.sum(OrderItem.total).desc())

    stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'product_name': row.product_name,
            'brand': row.product_brand or 'Без бренду',
            'revenue': float(row.revenue or Decimal('0')),
            'quantity': int(row.quantity or 0)
        }
        for row in rows
    ]


async def get_revenue_by_category(
    session: AsyncSession,
    date_from: date,
    date_to: date
) -> List[Dict[str, Any]]:
    """
    Get revenue distribution by category.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date

    Returns:
        List of dictionaries with category_name, revenue
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            Category.name.label('category_name'),
            func.sum(OrderItem.total).label('revenue')
        )
        .select_from(OrderItem)
        .join(Product, Product.id == OrderItem.product_id)
        .join(Category, Category.id == Product.category_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(OrderItem.total).desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'category_name': row.category_name,
            'revenue': float(row.revenue or Decimal('0'))
        }
        for row in rows
    ]


async def get_orders_by_status(
    session: AsyncSession,
    date_from: date,
    date_to: date
) -> List[Dict[str, Any]]:
    """
    Get orders count by status.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date

    Returns:
        List of dictionaries with status, count
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            Order.status,
            func.count(Order.id).label('count')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt
            )
        )
        .group_by(Order.status)
    )

    result = await session.execute(stmt)
    rows = result.all()

    # Ukrainian translations for statuses
    status_translations = {
        'created': 'Нове замовлення',
        'paid': 'Оплачено',
        'processing': 'В обробці',
        'shipped': 'Відправлено'
    }

    return [
        {
            'status': status_translations.get(row.status.value, row.status.value),
            'count': row.count
        }
        for row in rows
    ]


async def get_revenue_by_weekday(
    session: AsyncSession,
    date_from: date,
    date_to: date
) -> List[Dict[str, Any]]:
    """
    Get revenue distribution by weekdays.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date

    Returns:
        List of dictionaries with weekday, revenue, orders_count
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    # Extract weekday (0=Monday, 6=Sunday in PostgreSQL)
    weekday_extract = func.extract('dow', Order.created_at)

    stmt = (
        select(
            weekday_extract.label('weekday'),
            func.sum(Order.total).label('revenue'),
            func.count(Order.id).label('orders_count')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        .group_by('weekday')
        .order_by('weekday')
    )

    result = await session.execute(stmt)
    rows = result.all()

    # Ukrainian weekday names (PostgreSQL: 0=Sunday, 1=Monday, ..., 6=Saturday)
    weekday_names = {
        0: 'Неділя',
        1: 'Понеділок',
        2: 'Вівторок',
        3: 'Середа',
        4: 'Четвер',
        5: 'П\'ятниця',
        6: 'Субота'
    }

    return [
        {
            'weekday': weekday_names.get(int(row.weekday), 'Невідомо'),
            'weekday_num': int(row.weekday),
            'revenue': float(row.revenue or Decimal('0')),
            'orders_count': row.orders_count or 0
        }
        for row in rows
    ]


async def get_discount_analysis(
    session: AsyncSession,
    date_from: date,
    date_to: date
) -> Dict[str, Any]:
    """
    Analyze discount usage and impact.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date

    Returns:
        Dictionary with discount metrics
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    # Overall discount statistics
    stmt = (
        select(
            func.sum(Order.discount_amount).label('total_discounts'),
            func.sum(Order.subtotal).label('total_subtotal'),
            func.sum(Order.total).label('total_revenue'),
            func.count(Order.id).label('total_orders'),
            func.count(Order.id).filter(Order.discount_amount > 0).label('orders_with_discount'),
            func.count(Order.id).filter(Order.coupon_id.isnot(None)).label('orders_with_coupon')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
    )

    result = await session.execute(stmt)
    row = result.one()

    total_discounts = float(row.total_discounts or Decimal('0'))
    total_subtotal = float(row.total_subtotal or Decimal('0'))
    total_revenue = float(row.total_revenue or Decimal('0'))
    total_orders = row.total_orders or 0
    orders_with_discount = row.orders_with_discount or 0
    orders_with_coupon = row.orders_with_coupon or 0

    # Calculate average discount percentage
    avg_discount_pct = (total_discounts / total_subtotal * 100) if total_subtotal > 0 else 0

    return {
        'total_discounts': total_discounts,
        'total_subtotal': total_subtotal,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'orders_with_discount': orders_with_discount,
        'orders_with_coupon': orders_with_coupon,
        'avg_discount_pct': round(avg_discount_pct, 2),
        'discount_rate': round((orders_with_discount / total_orders * 100) if total_orders > 0 else 0, 2)
    }


async def get_dead_stock(
    session: AsyncSession,
    days_threshold: int = 30
) -> List[Dict[str, Any]]:
    """
    Get products that haven't been sold in the last X days.

    Args:
        session: Database session
        days_threshold: Number of days without sales to consider dead stock

    Returns:
        List of dictionaries with product info and days since last sale
    """
    from datetime import timedelta

    threshold_date = datetime.combine(
        date.today() - timedelta(days=days_threshold),
        datetime.min.time()
    )

    # Subquery to get last sale date for each product
    last_sale_subq = (
        select(
            OrderItem.product_id,
            func.max(Order.created_at).label('last_sale_date')
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED]))
        .group_by(OrderItem.product_id)
        .subquery()
    )

    # Get active products with no recent sales
    stmt = (
        select(
            Product.id,
            Product.name,
            Product.brand,
            Product.retail_price,
            Product.in_stock,
            last_sale_subq.c.last_sale_date
        )
        .outerjoin(last_sale_subq, Product.id == last_sale_subq.c.product_id)
        .where(
            and_(
                Product.is_active.is_(True),
                func.coalesce(last_sale_subq.c.last_sale_date, datetime.min) < threshold_date
            )
        )
        .order_by(last_sale_subq.c.last_sale_date.asc().nullsfirst())
        .limit(50)
    )

    result = await session.execute(stmt)
    rows = result.all()

    current_time = datetime.now()

    return [
        {
            'product_id': row.id,
            'product_name': row.name,
            'brand': row.brand or 'Без бренду',
            'price': float(row.retail_price),
            'in_stock': row.in_stock,
            'last_sale_date': row.last_sale_date.strftime('%Y-%m-%d') if row.last_sale_date else 'Ніколи',
            'days_since_sale': (current_time - row.last_sale_date).days if row.last_sale_date else 999
        }
        for row in rows
    ]


async def get_revenue_by_brand(
    session: AsyncSession,
    date_from: date,
    date_to: date
) -> List[Dict[str, Any]]:
    """
    Get revenue distribution by brand.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date

    Returns:
        List of dictionaries with brand, revenue
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            func.coalesce(Product.brand, 'Без бренду').label('brand'),
            func.sum(OrderItem.total).label('revenue')
        )
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .outerjoin(Product, Product.id == OrderItem.product_id)
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        .group_by(Product.brand)
        .order_by(func.sum(OrderItem.total).desc())
        .limit(10)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'brand': row.brand,
            'revenue': float(row.revenue or Decimal('0'))
        }
        for row in rows
    ]


async def get_aov_trend(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    granularity: str = 'day'
) -> List[Dict[str, Any]]:
    """
    Get Average Order Value trend over time.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date
        granularity: 'day', 'week', or 'month'

    Returns:
        List of dictionaries with date, aov, orders_count
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    # Determine truncation function based on granularity
    if granularity == 'day':
        trunc = func.date_trunc('day', Order.created_at)
    elif granularity == 'week':
        trunc = func.date_trunc('week', Order.created_at)
    else:
        trunc = func.date_trunc('month', Order.created_at)

    # Build query
    stmt = (
        select(
            trunc.label('period'),
            func.avg(Order.total).label('aov'),
            func.count(Order.id).label('orders_count')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        .group_by('period')
        .order_by('period')
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'date': row.period.strftime('%Y-%m-%d'),
            'aov': float(row.aov or Decimal('0')),
            'orders_count': row.orders_count or 0
        }
        for row in rows
    ]


async def get_orders_by_city(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get orders count by city.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date
        limit: Number of cities to return

    Returns:
        List of dictionaries with city, orders_count, revenue
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            Order.city,
            func.count(Order.id).label('orders_count'),
            func.sum(Order.total).label('revenue')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.city.isnot(None),
                Order.city != ''
            )
        )
        .group_by(Order.city)
        .order_by(func.count(Order.id).desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'city': row.city,
            'orders_count': row.orders_count or 0,
            'revenue': float(row.revenue or Decimal('0'))
        }
        for row in rows
    ]


async def get_customer_stats(
    session: AsyncSession,
    date_from: date,
    date_to: date
) -> Dict[str, Any]:
    """
    Get customer statistics (new vs repeat).

    Args:
        session: Database session
        date_from: Start date
        date_to: End date

    Returns:
        Dictionary with new_customers, repeat_customers counts
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    # Get unique customers (by phone) in period
    unique_customers_stmt = (
        select(func.count(func.distinct(Order.phone)))
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.phone.isnot(None)
            )
        )
    )
    total_customers = (await session.execute(unique_customers_stmt)).scalar() or 0

    # Simplified: assume all are new customers for MVP
    # TODO: Implement proper first-order tracking
    return {
        'total_customers': total_customers,
        'new_customers': total_customers,
        'repeat_customers': 0
    }


async def get_top_customers(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top customers by revenue.

    Args:
        session: Database session
        date_from: Start date
        date_to: End date
        limit: Number of customers to return

    Returns:
        List of dictionaries with customer info
    """
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            Order.phone,
            Order.full_name,
            func.count(Order.id).label('orders_count'),
            func.sum(Order.total).label('revenue')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED]),
                Order.phone.isnot(None)
            )
        )
        .group_by(Order.phone, Order.full_name)
        .order_by(func.sum(Order.total).desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'phone': row.phone,
            'name': row.full_name or 'Без імені',
            'orders_count': row.orders_count or 0,
            'revenue': float(row.revenue or Decimal('0'))
        }
        for row in rows
    ]


async def get_customers_by_city(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get customer count by city."""
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            Order.city,
            func.count(func.distinct(Order.phone)).label('customers_count')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.city.isnot(None),
                Order.city != ''
            )
        )
        .group_by(Order.city)
        .order_by(func.count(func.distinct(Order.phone)).desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'city': row.city,
            'customers_count': row.customers_count or 0
        }
        for row in rows
    ]


async def get_delivery_by_method(
    session: AsyncSession,
    date_from: date,
    date_to: date
) -> List[Dict[str, Any]]:
    """Get orders by delivery method."""
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            Order.delivery_method,
            func.count(Order.id).label('orders_count'),
            func.sum(Order.total).label('revenue')
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING, OrderStatus.SHIPPED])
            )
        )
        .group_by(Order.delivery_method)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'delivery_method': row.delivery_method,
            'orders_count': row.orders_count or 0,
            'revenue': float(row.revenue or Decimal('0'))
        }
        for row in rows
    ]


async def get_orders_without_ttn(
    session: AsyncSession,
    date_from: date,
    date_to: date,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get orders without TTN tracking."""
    start_dt = datetime.combine(date_from, datetime.min.time())
    end_dt = datetime.combine(date_to, datetime.max.time())

    stmt = (
        select(
            Order.id,
            Order.full_name,
            Order.city,
            Order.delivery_method,
            Order.status,
            Order.created_at
        )
        .where(
            and_(
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
                Order.status.in_([OrderStatus.PAID, OrderStatus.PROCESSING]),
                func.coalesce(Order.ttn, '') == ''
            )
        )
        .order_by(Order.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            'order_id': row.id,
            'full_name': row.full_name or 'Без імені',
            'city': row.city or 'Не вказано',
            'delivery_method': row.delivery_method,
            'status': row.status.value,
            'created_at': row.created_at.isoformat()
        }
        for row in rows
    ]
