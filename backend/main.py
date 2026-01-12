"""
FastAPI 应用入口

初始化 FastAPI 应用，配置中间件、路由等。
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging
import time

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from core.logger import logger
from core.exceptions import ResonaException
from api.v1 import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 Resona Backend Service Starting...")
    logger.info(f"📝 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🤖 LLM Backend: {settings.LLM_BACKEND}")
    logger.info(f"🔧 Log Level: {settings.LOG_LEVEL}")
    
    yield
    
    # 关闭时执行
    logger.info("👋 Resona Backend Service Shutting Down...")


class _HealthAccessLogFilter(logging.Filter):
    """过滤 uvicorn access log 中的 health 请求，避免刷屏。"""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # uvicorn.access 的默认格式类似：
        # 172.19.0.1:12345 - "GET /api/v1/health HTTP/1.1" 200
        return "/api/v1/health" not in msg


# 彻底屏蔽 /api/v1/health 的 access log（即使开启了 access log 也不会刷屏）
_health_filter = _HealthAccessLogFilter()


def _attach_health_filter(_logger: logging.Logger) -> None:
    """把 health 过滤器挂到 logger 以及它的 handlers 上（幂等）。"""
    if not any(isinstance(f, _HealthAccessLogFilter) for f in _logger.filters):
        _logger.addFilter(_health_filter)
    for _h in _logger.handlers:
        if not any(isinstance(f, _HealthAccessLogFilter) for f in _h.filters):
            _h.addFilter(_health_filter)


# 关键：uvicorn access log 可能会 propagate 到 root logger 的 handler
# 为了保证“无论如何都不刷屏”，我们同时过滤 uvicorn.access + root handlers。
_attach_health_filter(logging.getLogger("uvicorn.access"))
_attach_health_filter(logging.getLogger())  # root logger


# 创建 FastAPI 应用
app = FastAPI(
    title="Resona API",
    description="基于 MBTI 约束的高情商社交 AI 助手",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求日志（跳过健康检查）"""
    start_time = time.time()
    
    # 跳过健康检查日志（避免刷屏）
    is_health_check = request.url.path == "/api/v1/health"
    
    # 记录请求信息
    if not is_health_check:
        logger.info(f"📨 {request.method} {request.url.path} - Client: {request.client.host}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    if not is_health_check:
        logger.info(
            f"✅ {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
    
    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# 全局异常处理
@app.exception_handler(ResonaException)
async def resona_exception_handler(request: Request, exc: ResonaException):
    """处理自定义异常"""
    logger.error(f"❌ ResonaException: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": str(exc),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理全局异常"""
    logger.exception(f"💥 Unhandled Exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "detail": str(exc) if settings.ENVIRONMENT == "development" else "请联系管理员",
        },
    )


# 根路径
@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {
        "message": "Welcome to Resona API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# 注册路由
from api.v1 import reply, user

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(reply.router, prefix="/api/v1/reply", tags=["Reply"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,  # 禁用访问日志（避免健康检查刷屏）
    )
