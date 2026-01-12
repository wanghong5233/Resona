"""
Health Check API

健康检查接口，用于监控服务状态。
"""

from fastapi import APIRouter
from datetime import datetime

from schemas.response import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    健康检查接口
    
    返回服务状态、版本和当前时间戳。
    """
    return HealthCheckResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
