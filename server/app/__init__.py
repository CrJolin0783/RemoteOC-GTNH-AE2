from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from models import StandardResponseModel
from config import __version__
from .task import router as commands_router
from .automate import router as automate_router
from .info import router as info_router
from .database import router as database_router
from .websocket import websocket_endpoint


app = FastAPI(title="RemoteOC", description="RemoteOC的服务端", version=__version__)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """
    捕获 HTTPException 并将其转化为 200 响应
    """
    return JSONResponse(
        status_code=500 if exc.status_code == 500 else 200,
        content=StandardResponseModel(
            code=exc.status_code,
            message=exc.detail,
            data=None,
        ).dict(),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(commands_router, prefix="/api/task", tags=["task"])
app.include_router(automate_router, prefix="/api/automate", tags=["automate"])
app.include_router(info_router, prefix="/api/info", tags=["info"])
app.include_router(database_router, prefix="/api/database", tags=["database"])

app.websocket("/ws/{client_id}")(websocket_endpoint)

