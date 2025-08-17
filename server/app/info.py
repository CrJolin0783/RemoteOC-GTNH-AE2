from config import SERVER_TOKEN
from utils.device import device_manager
from config import __version__
from fastapi import APIRouter, Depends, HTTPException, Header
from models import *


router = APIRouter()


async def token_required(x_server_token: str = Header(...)):
    """Token 验证依赖"""
    if x_server_token != SERVER_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized, invalid token")


@router.get("/meta", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_meta():
    """获取服务端信息"""
    return StandardResponseModel(
        code=200,
        message="获取成功",
        data={
            "version": __version__,
            "device_num": device_manager.get_device_num(),
        },
    )


@router.get("/version", response_model=StandardResponseModel)
async def get_meta():
    """获取服务端版本信息"""
    return StandardResponseModel(
        code=200,
        message="获取成功",
        data={"version": __version__},
    )


@router.get("/devices", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_devices():
    """获取客户端列表"""
    return StandardResponseModel(
        code=200,
        message="获取成功",
        data=device_manager.get_devices(),
    )