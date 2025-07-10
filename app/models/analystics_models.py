from typing import Dict, List, Any

from pydantic import BaseModel


class DateRangeAnalytics(BaseModel):
    """Response model for date range analytics"""
    date_range: Dict[str, str]
    total_appointments: int
    no_show_rate: float
    total_calls: int
    average_call_duration: float
    department_wise_stats: List[Dict[str, Any]]
    call_trends: List[Dict[str, Any]]
    appointment_trends: List[Dict[str, Any]]
    call_status_distribution: List[Dict[str, Any]]
    appointment_status_distribution: List[Dict[str, Any]]
    generated_at: str


class DashboardMetrics(BaseModel):
    """Response model for dashboard overview"""
    overview: Dict[str, Any]
    trends: Dict[str, Any]
    department_performance: List[Dict[str, Any]]
    call_analytics: Dict[str, Any]