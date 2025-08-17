from config import SERVER_TOKEN, action_template
from utils.utils import *
from utils.trigger import trigger_manager
from utils.timer import timer_manager
from fastapi import APIRouter, Depends, HTTPException, Header
from models import *

import json


router = APIRouter()


async def token_required(x_server_token: str = Header(...)):
    """Token 验证依赖"""
    if x_server_token != SERVER_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized, invalid token")


@router.get("/trigger/config", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_trigger_config():
    """获取可用触发器配置列表"""
    return {"code": 200, "message": "success", "data": trigger_manager.get_config_list()}


@router.post("/trigger/add", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def add_trigger(trigger: AddTriggerModel):
    """添加触发器"""
    trigger_task_id = trigger_manager.register_trigger(
        trigger.name,
        trigger.action,
        trigger.trigger_kwargs,
        trigger.action_kwargs,
        trigger.interval
    )
    return {"code": 200, "message": "success", "data": {"trigger_task_id": trigger_task_id}}


@router.post("/trigger/remove", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def remove_trigger(trigger: TriggerRequestModel):
    """移除触发器"""
    trigger_manager.unregister_trigger(trigger.trigger_task_id)
    return {"code": 200, "message": "success"}


@router.get("/trigger/list", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_trigger_list():
    """获取所有触发器"""
    trigger_list = trigger_manager.get_trigger_list()
    # 去除函数对象，避免序列化错误
    temp = json.dumps(trigger_list, default=lambda x: None)
    trigger_list = json.loads(temp)
    return {"code": 200, "message": "success", "data": trigger_list}


@router.post("/trigger/start", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def start_trigger(trigger: TriggerRequestModel):
    """启动触发器"""
    trigger_manager.start(trigger.trigger_task_id)
    return {"code": 200, "message": "success"}


@router.post("/trigger/stop", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def stop_trigger(trigger: TriggerRequestModel):
    """停止触发器"""
    trigger_manager.stop(trigger.trigger_task_id)
    return {"code": 200, "message": "success"}


@router.get("/timer/config", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_timer_config():
    """获取可用定时器配置列表"""
    return {"code": 200, "message": "success", "data": timer_manager.get_config_list()}


@router.post("/timer/add", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def add_timer(timer: AddTimerModel):
    """添加定时器"""
    timer_id = timer_manager.register_timer(
        timer.name,
        timer.action,
        timer.trigger_kwargs,
        timer.action_kwargs,
    )
    return {"code": 200, "message": "success", "data": {"timer_id": timer_id}}


@router.post("/timer/remove", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def remove_timer(timer: TimerRequestModel):
    """移除定时器"""
    timer_manager.unregister_timer(timer.timer_id)
    return {"code": 200, "message": "success"}


@router.get("/timer/list", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_timer_list():
    """获取所有定时器"""
    timer_list = timer_manager.get_timer_list()
    # 去除函数对象，避免序列化错误
    temp = json.dumps(timer_list, default=lambda x: None)
    timer_list = json.loads(temp)
    return {"code": 200, "message": "success", "data": timer_list}


@router.post("/timer/start", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def start_timer(timer: TimerRequestModel):
    """启动定时器"""
    timer_manager.start(timer.timer_id)
    return {"code": 200, "message": "success"}


@router.post("/timer/stop", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def stop_timer(timer: TimerRequestModel):
    """停止定时器"""
    timer_manager.stop(timer.timer_id)
    return {"code": 200, "message": "success"}


@router.get("/action/template", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_action_template():
    """获取可用 Action 模板"""
    return {"code": 200, "message": "success", "data": action_template}