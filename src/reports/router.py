"""FastAPI routers for reports module."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_manager_or_admin
from src.database import get_async_session
from src.products.models import Product, Category
from src.reports.charts import format_line_chart
from src.reports.queries import (
    get_sales_trend,
    get_top_products,
    get_revenue_by_category,
    get_orders_by_status,
    get_revenue_by_weekday,
    get_revenue_by_brand,
    get_aov_trend,
    get_orders_by_city
)
from src.reports.schemas import ReportFilters, PeriodType
from src.reports.service import (
    get_overview_stats,
    calculate_date_range,
    get_sales_report,
    get_products_report,
    get_orders_report,
    get_customers_report,
    get_financial_report,
    get_delivery_report
)
from src.templating import templates
from src.users.models import User

router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
async def reports_overview(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    category_id: Optional[int] = None,
    brand: Optional[str] = None,
    compare_previous: bool = False,
):
    """Main reports page with tabs."""
    # Get categories for filter
    categories_stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
    categories_result = await session.execute(categories_stmt)
    categories = list(categories_result.scalars().all())

    # Get unique brands for filter
    brands_stmt = select(Product.brand).distinct().where(
        Product.is_active.is_(True),
        Product.brand.isnot(None),
        Product.brand != ''
    ).order_by(Product.brand)
    brands_result = await session.execute(brands_stmt)
    brands = [brand for brand in brands_result.scalars().all() if brand]

    # Build filters
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        brand=brand,
        compare_previous=compare_previous
    )

    # Get overview statistics
    stats = await get_overview_stats(session, filters)

    return templates.TemplateResponse(
        "admin/reports/overview.html",
        {
            "request": request,
            "user": user,
            "active_page": "reports",
            "categories": categories,
            "brands": brands,
            "stats": stats,
        },
    )


@router.get("/reports/api/chart/sales-trend")
async def chart_sales_trend(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for sales trend chart data."""
    # Build filters
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get sales trend data
    trend_data = await get_sales_trend(session, start_date, end_date, granularity='day')

    # Format for Chart.js
    labels = [item['date'] for item in trend_data]
    revenue_data = [item['revenue'] for item in trend_data]
    orders_data = [item['orders_count'] for item in trend_data]

    # Build chart data with dual axis
    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Виручка (₴)",
                    "data": revenue_data,
                    "borderColor": "rgb(236, 72, 153)",
                    "backgroundColor": "rgba(236, 72, 153, 0.1)",
                    "tension": 0.4,
                    "fill": True,
                    "yAxisID": "y",
                },
                {
                    "label": "Замовлення",
                    "data": orders_data,
                    "borderColor": "rgb(59, 130, 246)",
                    "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    "tension": 0.4,
                    "fill": False,
                    "yAxisID": "y1",
                }
            ]
        },
        "options": {
            "scales": {
                "y": {
                    "type": "linear",
                    "position": "left",
                    "title": {
                        "display": True,
                        "text": "Виручка (₴)"
                    },
                    "ticks": {
                        "callback": "##function(value) { return value.toLocaleString('uk-UA'); }##"
                    }
                },
                "y1": {
                    "type": "linear",
                    "position": "right",
                    "title": {
                        "display": True,
                        "text": "Замовлення"
                    },
                    "grid": {
                        "drawOnChartArea": False
                    }
                }
            }
        }
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/chart/top-products")
async def chart_top_products(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for top products bar chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get top products data
    top_products = await get_top_products(session, start_date, end_date, limit=5)

    # Format for Chart.js
    labels = [item['product_name'] for item in top_products]
    data = [item['revenue'] for item in top_products]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Виручка (₴)",
                    "data": data,
                    "backgroundColor": [
                        "rgba(236, 72, 153, 0.8)",
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(16, 185, 129, 0.8)",
                        "rgba(245, 158, 11, 0.8)",
                        "rgba(139, 92, 246, 0.8)",
                    ],
                    "borderWidth": 0,
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/chart/categories-distribution")
async def chart_categories_distribution(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for categories distribution pie chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get revenue by category
    categories_data = await get_revenue_by_category(session, start_date, end_date)

    # Format for Chart.js
    labels = [item['category_name'] for item in categories_data]
    data = [item['revenue'] for item in categories_data]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": [
                        "rgba(236, 72, 153, 0.8)",
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(16, 185, 129, 0.8)",
                        "rgba(245, 158, 11, 0.8)",
                        "rgba(139, 92, 246, 0.8)",
                        "rgba(244, 63, 94, 0.8)",
                        "rgba(99, 102, 241, 0.8)",
                    ],
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/chart/orders-by-status")
async def chart_orders_by_status(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for orders by status doughnut chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get orders by status
    status_data = await get_orders_by_status(session, start_date, end_date)

    # Format for Chart.js
    labels = [item['status'] for item in status_data]
    data = [item['count'] for item in status_data]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": [
                        "rgba(245, 158, 11, 0.8)",  # created - yellow
                        "rgba(16, 185, 129, 0.8)",  # paid - green
                        "rgba(59, 130, 246, 0.8)",  # processing - blue
                        "rgba(236, 72, 153, 0.8)",  # shipped - pink
                    ],
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/chart/revenue-by-weekday")
async def chart_revenue_by_weekday(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for revenue by weekday bar chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get revenue by weekday
    weekday_data = await get_revenue_by_weekday(session, start_date, end_date)

    # Sort by weekday_num to ensure proper ordering (Monday-Sunday)
    weekday_data = sorted(weekday_data, key=lambda x: (x['weekday_num'] + 6) % 7)

    # Format for Chart.js
    labels = [item['weekday'] for item in weekday_data]
    data = [item['revenue'] for item in weekday_data]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Виручка (₴)",
                    "data": data,
                    "backgroundColor": [
                        "rgba(59, 130, 246, 0.8)",    # Monday - blue
                        "rgba(16, 185, 129, 0.8)",    # Tuesday - green
                        "rgba(245, 158, 11, 0.8)",    # Wednesday - yellow
                        "rgba(236, 72, 153, 0.8)",    # Thursday - pink
                        "rgba(139, 92, 246, 0.8)",    # Friday - purple
                        "rgba(244, 63, 94, 0.8)",     # Saturday - rose
                        "rgba(99, 102, 241, 0.8)",    # Sunday - indigo
                    ],
                    "borderWidth": 0,
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/sales-report")
async def api_sales_report(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for sales report data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    sales_data = await get_sales_report(session, filters)

    return JSONResponse(content=sales_data)


@router.get("/reports/api/chart/revenue-by-brand")
async def chart_revenue_by_brand(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for revenue by brand pie chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get revenue by brand
    brand_data = await get_revenue_by_brand(session, start_date, end_date)

    # Format for Chart.js
    labels = [item['brand'] for item in brand_data]
    data = [item['revenue'] for item in brand_data]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "data": data,
                    "backgroundColor": [
                        "rgba(236, 72, 153, 0.8)",
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(16, 185, 129, 0.8)",
                        "rgba(245, 158, 11, 0.8)",
                        "rgba(139, 92, 246, 0.8)",
                        "rgba(244, 63, 94, 0.8)",
                        "rgba(99, 102, 241, 0.8)",
                        "rgba(168, 85, 247, 0.8)",
                        "rgba(34, 197, 94, 0.8)",
                        "rgba(249, 115, 22, 0.8)",
                    ],
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/chart/top-products-by-quantity")
async def chart_top_products_by_quantity(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for top products by quantity bar chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get top products by quantity
    top_products = await get_top_products(session, start_date, end_date, limit=10, order_by='quantity')

    # Format for Chart.js
    labels = [item['product_name'] for item in top_products]
    data = [item['quantity'] for item in top_products]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Продано (шт)",
                    "data": data,
                    "backgroundColor": [
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(16, 185, 129, 0.8)",
                        "rgba(245, 158, 11, 0.8)",
                        "rgba(236, 72, 153, 0.8)",
                        "rgba(139, 92, 246, 0.8)",
                        "rgba(244, 63, 94, 0.8)",
                        "rgba(99, 102, 241, 0.8)",
                        "rgba(168, 85, 247, 0.8)",
                        "rgba(34, 197, 94, 0.8)",
                        "rgba(249, 115, 22, 0.8)",
                    ],
                    "borderWidth": 0,
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/products-report")
async def api_products_report(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for products report data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    products_data = await get_products_report(session, filters)

    return JSONResponse(content=products_data)


@router.get("/reports/api/chart/aov-trend")
async def chart_aov_trend(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for AOV trend chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get AOV trend data
    trend_data = await get_aov_trend(session, start_date, end_date, granularity='day')

    # Format for Chart.js
    labels = [item['date'] for item in trend_data]
    data = [item['aov'] for item in trend_data]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Середній чек (₴)",
                    "data": data,
                    "borderColor": "rgb(139, 92, 246)",
                    "backgroundColor": "rgba(139, 92, 246, 0.1)",
                    "tension": 0.4,
                    "fill": True,
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/chart/orders-by-city")
async def chart_orders_by_city(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for orders by city bar chart data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    start_date, end_date = calculate_date_range(filters)

    # Get orders by city
    city_data = await get_orders_by_city(session, start_date, end_date, limit=10)

    # Format for Chart.js
    labels = [item['city'] for item in city_data]
    data = [item['orders_count'] for item in city_data]

    chart_response = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Кількість замовлень",
                    "data": data,
                    "backgroundColor": [
                        "rgba(236, 72, 153, 0.8)",
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(16, 185, 129, 0.8)",
                        "rgba(245, 158, 11, 0.8)",
                        "rgba(139, 92, 246, 0.8)",
                        "rgba(244, 63, 94, 0.8)",
                        "rgba(99, 102, 241, 0.8)",
                        "rgba(168, 85, 247, 0.8)",
                        "rgba(34, 197, 94, 0.8)",
                        "rgba(249, 115, 22, 0.8)",
                    ],
                    "borderWidth": 0,
                }
            ]
        },
        "options": {}
    }

    return JSONResponse(content=chart_response)


@router.get("/reports/api/orders-report")
async def api_orders_report(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for orders report data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    orders_data = await get_orders_report(session, filters)

    return JSONResponse(content=orders_data)


@router.get("/reports/api/customers-report")
async def api_customers_report(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for customers report data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    customers_data = await get_customers_report(session, filters)

    return JSONResponse(content=customers_data)


@router.get("/reports/api/financial-report")
async def api_financial_report(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for financial report data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    financial_data = await get_financial_report(session, filters)

    return JSONResponse(content=financial_data)


@router.get("/reports/api/delivery-report")
async def api_delivery_report(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_manager_or_admin),
    period: PeriodType = Query(PeriodType.MONTH),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """API endpoint for delivery report data."""
    filters = ReportFilters(
        period=period,
        date_from=date_from,
        date_to=date_to,
    )

    delivery_data = await get_delivery_report(session, filters)

    return JSONResponse(content=delivery_data)
