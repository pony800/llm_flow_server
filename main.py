import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import flow_router, file_router, node_router, exec_router, config_router

class AppConfig:
    CORS_ORIGINS = ["*"]
    ALLOWED_METHODS = ["POST", "GET", "OPTIONS"]

app = FastAPI(title="AI Flow API", version="0.1.0")

# 添加中间件
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=AppConfig.CORS_ORIGINS,
    allow_methods=AppConfig.ALLOWED_METHODS,
    allow_headers=["*"],
)

# 包含路由
app.include_router(flow_router.router, prefix="/api")
app.include_router(file_router.router, prefix="/api")
app.include_router(node_router.router, prefix="/api")
app.include_router(config_router.router, prefix="/api")
app.include_router(exec_router.router, prefix="/ws")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)