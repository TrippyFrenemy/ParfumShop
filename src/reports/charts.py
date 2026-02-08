"""Chart.js data formatting utilities."""
from typing import List, Dict, Any, Optional


def format_line_chart(
    data: List[Any],
    labels: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format data for Chart.js line chart."""
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Data",
                    "data": data,
                    "borderColor": "rgb(236, 72, 153)",
                    "backgroundColor": "rgba(236, 72, 153, 0.1)",
                    "tension": 0.4,
                    "fill": True,
                }
            ]
        },
        "options": options or {}
    }


def format_bar_chart(
    data: List[Any],
    labels: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format data for Chart.js bar chart."""
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Data",
                    "data": data,
                    "backgroundColor": "rgba(236, 72, 153, 0.8)",
                }
            ]
        },
        "options": options or {}
    }


def format_pie_chart(
    data: List[Any],
    labels: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format data for Chart.js pie chart."""
    return {
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
                    ],
                }
            ]
        },
        "options": options or {}
    }


def format_doughnut_chart(
    data: List[Any],
    labels: List[str],
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format data for Chart.js doughnut chart."""
    return {
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
                    ],
                }
            ]
        },
        "options": options or {}
    }
