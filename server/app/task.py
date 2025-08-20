from config import timer_task_config, task_config, SERVER_TOKEN
from utils.utils import *
from utils.trigger import trigger_manager
from utils.task import task_manager
from utils.device import device_manager
from utils.cache import cache, incremental_sync, distributed_cache
from utils.serialization import serializer, optimizer
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, Form
from models import *
import json
import re
import uuid
import gzip
import base64
import time
from typing import Optional


router = APIRouter()


async def token_required(x_server_token: str = Header(...)):
    """Token 验证依赖"""
    if x_server_token != SERVER_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized, invalid token")


@router.get("/get", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_commands(x_client_id: Optional[str] = Header(None, description="客户端id"), 
                      incremental: bool = Query(False, description="启用增量同步"),
                      optimized: bool = Query(True, description="启用数据优化")):
    """
    获取任务中的指令，返回第一个处于 READY 状态的任务
    """
    task_id = None
    task_list = task_manager.list_tasks()
    device_manager.record_device(x_client_id)

    for tid in task_list:
        task = task_manager.get_task(tid)
        if task:
            task_client_id = task.get("client_id")
            if task["status"] == READY and (not task_client_id or not x_client_id or task_client_id == x_client_id):
                task_id = tid
                break

    if task_id:
        task = task_manager.get_task(task_id)
        commands = task.get("commands", [])
        is_chunked = task.get("chunked", False)
        
        # 检查是否为缓存任务，支持增量同步
        if incremental and task_id in task_config and task_config[task_id].get('cache', False):
            cache_key = f"{x_client_id}_{task_id}"
            cached_data = distributed_cache.get(cache_key)
            
            if cached_data:
                # 使用分布式缓存的增量同步
                current_fingerprint = cached_data['fingerprint']
                last_known_fingerprint = cached_data.get('last_known_fingerprint')
                
                if last_known_fingerprint == current_fingerprint:
                    return {
                        "code": 200, 
                        "message": "No data changes detected", 
                        "data": {
                            "taskId": task_id, 
                            "commands": [], 
                            "is_chunked": False,
                            "sync_type": "no_change",
                            "fingerprint": current_fingerprint
                        }
                    }
        
        # 优化命令数据
        optimized_commands = []
        if optimized and commands:
            for cmd in commands:
                if isinstance(cmd, str) and "ae.getAllItems" in cmd:
                    optimized_commands.append("return ae.getAllSilempleItems()")
                else:
                    optimized_commands.append(cmd)
        else:
            optimized_commands = commands
        
        task_manager.update_task(task_id, status=PENDING)
        return {
            "code": 200, 
            "message": f"Commands for task fetched successfully", 
            "data": {
                "taskId": task_id, 
                "commands": optimized_commands, 
                "is_chunked": is_chunked,
                "optimized": optimized,
                "incremental": incremental
            }
        }
    else:
        return {"code": 200, "message": "No ready commands available", "data": None}


@router.post("/chunked_report", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def receive_chunked_report(request: Request, chunked: int = Query(-1, description="是否为分块上传，1表示开始，0表示结束，>1 表示继续上传"), x_client_id: Optional[str] = Header(None, description="客户端id")):
    """
    接收客户端的任务执行后的结果, 仅用于分块上传
    """
    try:
        body = await request.body()  # OC返回数据为GBK，直接使用pydantic解析会报400错误
        decoded_body = decode_request_body(body)
        json_data = json.loads(decoded_body)
        command_result = CommandChunkedResultModel(**json_data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {str(e)}")
        raise HTTPException(status_code=400, detail="JSON 格式错误")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = command_result.task_id
    results = command_result.results

    if not task_manager.task_exists(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    # 如果 chunked == 1，则开始接收分块任务，覆盖已有数据，并将状态设置为 UPLOADING
    if chunked == 1:
        task = task_manager.get_task(task_id)
        if task:
            logger.debug(f"Task {task_id} already exists, resetting task with new data.")
        # 重置任务数据并设置状态为 UPLOADING
        task_manager.update_task(task_id, status=UPLOADING, results=results)
        return {"code": 200, "message": f"Chunked data for task received and reset successfully", "data": {"taskId": task_id}}

    # 如果 chunked > 1，则继续接收分块数据，添加进已有的任务里
    elif chunked > 1:
        task = task_manager.get_task(task_id)
        if task.get("status") != UPLOADING:
            return {"code": 200, "message": f"Task status is not uploading", "data": {"taskId": task_id}}
        if task and "results" in task:
            existing_results = task.get("results", [])
            if isinstance(existing_results, list) and isinstance(results, list):
                existing_results.extend(results)  # 添加到已有的结果里
            task_manager.update_task(task_id, status=UPLOADING, results=existing_results)
            return {"code": 200, "message": f"Chunked data for task added successfully", "data": {"taskId": task_id}}
        else:
            return {"code": 400, "message": f"task results is none", "data": {"taskId": task_id}}

    # 为0时，表示接收完成，合并数据并更新任务状态为 COMPLETED
    elif chunked == 0:
        device_manager.record_device(x_client_id, 'chunked_report')
        task = task_manager.get_task(task_id)
        if task and "results" in task:
            existing_results = task.get("results", [])
            if isinstance(existing_results, list) and isinstance(results, list):
                existing_results.extend(results)  # 合并数据
            final_results = existing_results
        else:
            final_results = results

        # 优化和缓存结果数据
        optimized_results = []
        if isinstance(final_results, list):
            for result in final_results:
                if isinstance(result, dict) and 'message' in result and result['message'] == 'success':
                    data = result.get('data', [])
                    if isinstance(data, list):
                        # 优化物品数据
                        optimized_data = optimizer.optimize_item_data(data)
                        optimized_results.append({'message': 'success', 'data': optimized_data})
                    else:
                        optimized_results.append(result)
                else:
                    optimized_results.append(result)
        else:
            optimized_results = final_results

        # 缓存结果以支持增量同步
        if task_id in task_config and task_config[task_id].get('cache', False):
            cache_key = f"{x_client_id}_{task_id}"
            incremental_sync.update_data(x_client_id, task_id, optimized_results)

        task_manager.update_task(task_id, status=COMPLETED, results=optimized_results)

        for config in [timer_task_config, task_config]:
            if task_id in config:
                handle = config.get(task_id, {}).get("handle")
                if handle:
                    results = handle(results)
                callback = config.get(task_id, {}).get("callback")
                if callback:
                    callback(results)

        return {"code": 200, "message": f"Task result received and completed", "data": {"taskId": task_id}}

    else:
        raise HTTPException(status_code=400, detail="Invalid value for chunked. Must be 0 or 1 or greater than 1")


@router.post("/report", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def receive_report(request: Request, x_client_id: Optional[str] = Header(None, description="客户端id")):
    """
    接收客户端的任务执行后的结果
    """
    try:
        body = await request.body()  # OC返回数据为GBK，直接使用pydantic解析会报400错误
        decoded_body = decode_request_body(body)
        json_data = json.loads(decoded_body)
        command_result = CommandResultModel(**json_data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {str(e)}")
        raise HTTPException(status_code=400, detail="JSON 格式错误")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    device_manager.record_device(x_client_id, 'report')
    task_id = command_result.task_id
    results = command_result.results

    if not task_manager.task_exists(task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    for config in [timer_task_config, task_config, trigger_manager.get_tasks()]:
        if task_id in config:
            handle = config.get(task_id, {}).get("handle")
            if handle:
                results = handle(results)
            callback = config.get(task_id, {}).get("callback")
            if callback:
                callback(results)

    task_manager.update_task(task_id, status=COMPLETED, results=results)
    return {"code": 200, "message": f"Task result received", "data": {"taskId": task_id}}


@router.post("/add", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def add_command(data: AddCommandModel):
    """新建任务，可自定义taskId，否则返回随机taskId"""
    task_id = data.task_id or str(uuid.uuid4())
    new_commands = data.commands
    client_id = data.client_id

    if not re.match(r"^[a-zA-Z0-9_-]+$", task_id):
        return {"code": 400, "message": "Invalid taskId format", "data": None}

    if not new_commands or not isinstance(new_commands, list) or len(new_commands) == 0:
        return {"code": 400, "message": "No commands provided or invalid format", "data": None}

    task_manager.add_task(task_id, client_id, new_commands, READY)
    return {"code": 200, "message": f"Task added with {len(new_commands)} command(s)", "data": {"taskId": task_id}}


@router.get("/status", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_task_status(
    task_id: str = Query(..., description="任务id"), 
    remove: bool = Query(True, description="如果任务为完成状态是否删除"),
    use_gzip: bool = Query(False, description="对reuslt进行gzip压缩并返回base64编码"),
):
    """
    获取指定task_id的任务状态
    """
    task = task_manager.get_task(task_id)
    if not task:
        return {"code": 404, "message": "Task not found", "data": None}

    status = task.get("status")
    if status == COMPLETED and remove:
        if task_id not in timer_task_config and task_id not in task_config:
            task_manager.remove_task(task_id)
    if use_gzip and task.get("results"):
        gzip_result = gzip.compress(json.dumps(task.get("results")).encode(), compresslevel=6)
        result = base64.b64encode(gzip_result).decode()
    else:
        result = task.get("results")
    return {
        "code": 200,
        "message": "success",
        "data": {
            "gzip": use_gzip,
            "taskId": task_id,
            "status": status,
            "result": result,
            "created_time": task.get("created_time"),
            "pending_time": task.get("pending_time"),
            "completed_time": task.get("completed_time"),
        },
    }


@router.post("/task", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def add_task_by_name(data: AddTaskByNameModel):
    """
    以任务的形式添加命令组，任务需要在配置文件中设置
    """
    task_id = data.task_id
    client_id = data.client_id
    params = data.params or {}

    # 从 task_config 中查找相应的任务
    task_config_entry = task_config.get(task_id)
    if not task_config_entry:
        return {"code": 404, "message": f"Task config not found for task name: {task_id}", "data": {"taskId": task_id}}

    commands = task_config_entry.get("commands", [])
    if len(commands) == 0:
        return {"code": 400, "message": f"Commands error for task name: {task_id}", "data": {"taskId": task_id}}
    is_chunked = task_config_entry.get("chunked", False)

    if not commands:
        return {"code": 400, "message": f"No commands found for task name: {task_id}", "data": {"taskId": task_id}}

    # 处理动态参数
    processed_commands = []
    dynamic_params = task_config_entry.get("dynamic_params", {})
    
    for cmd in commands:
        processed_cmd = cmd
        
        # 替换动态参数
        for param_name, param_config in dynamic_params.items():
            param_value = params.get(param_name, param_config.get("default", None))
            if param_value is not None:
                # 根据参数类型进行格式化
                param_type = param_config.get("type", "str")
                if param_type == "dict":
                    param_str = json.dumps(param_value)
                elif param_type == "int":
                    param_str = str(param_value)
                elif param_type == "bool":
                    param_str = "true" if param_value else "false"
                else:
                    param_str = str(param_value)
                
                # 替换命令中的占位符
                processed_cmd = processed_cmd.replace(f"{{{param_name}}}", param_str)
        
        processed_commands.append(processed_cmd)

    # 将任务加入任务管理器
    if task_config_entry.get('cache', False):
        if not task_manager.update_task(task_id, status=READY):
            # 没有任务则创建新任务
            task_manager.add_task(task_id, client_id, processed_commands, READY, is_chunked=is_chunked)
    else:
        task_manager.add_task(task_id, client_id, processed_commands, READY, is_chunked=is_chunked)

    return {"code": 200, "message": f"Task added with {len(processed_commands)} command(s)", "data": {"taskId": task_id}}


@router.get("/cache/stats", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_cache_stats():
    """获取缓存统计信息"""
    stats = distributed_cache.stats()
    return {"code": 200, "message": "Cache statistics retrieved", "data": stats}


@router.post("/cache/clear", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def clear_cache():
    """清空缓存"""
    distributed_cache.clear()
    return {"code": 200, "message": "Cache cleared successfully", "data": None}


@router.get("/cache/get", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_cache_data(key: str = Query(..., description="缓存键")):
    """获取缓存数据"""
    data = distributed_cache.get(key)
    if data:
        return {"code": 200, "message": "Cache data retrieved", "data": data}
    else:
        return {"code": 404, "message": "Cache key not found", "data": None}


@router.post("/cache/set", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def set_cache_data(key: str = Form(..., description="缓存键"), 
                        data: str = Form(..., description="缓存数据"),
                        ttl: int = Form(300, description="缓存时间（秒）")):
    """设置缓存数据"""
    import json
    try:
        data_dict = json.loads(data)
        result = distributed_cache.set(key, data_dict, ttl)
        return {"code": 200, "message": "Cache data set", "data": {"result": result}}
    except json.JSONDecodeError:
        return {"code": 400, "message": "Invalid JSON data", "data": None}


@router.get("/cache/data", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_cached_data(data_type: str = Query(..., description="数据类型: cpu, item")):
    """
    获取缓存的AE2数据
    """
    cache_key = f"ae_{data_type}_data"
    cached_data = distributed_cache.get(cache_key)
    
    if cached_data:
        return {
            "code": 200,
            "message": "Cached data retrieved successfully",
            "data": cached_data
        }
    else:
        return {
            "code": 404,
            "message": "Cached data not found",
            "data": None
        }


@router.post("/cache/upload", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def upload_data_to_cache(request: Request, x_client_id: Optional[str] = Header(None, description="客户端id")):
    """
    上传数据到缓存
    """
    try:
        body = await request.body()
        decoded_body = decode_request_body(body)
        json_data = json.loads(decoded_body)
        
        data_type = json_data.get("type")
        data = json_data.get("data")
        timestamp = json_data.get("timestamp")
        
        if not data_type or not data:
            return {"code": 400, "message": "Missing type or data", "data": None}
        
        cache_key = f"ae_{data_type}_data"
        cached_result = distributed_cache.set(cache_key, {
            "data": data,
            "type": data_type,
            "timestamp": timestamp,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "client_id": x_client_id
        }, ttl=300)  # 缓存5分钟
        
        return {
            "code": 200,
            "message": f"Data uploaded to cache successfully with key: {cache_key}",
            "data": {"cache_key": cache_key, "result": cached_result}
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {str(e)}")
        raise HTTPException(status_code=400, detail="JSON 格式错误")
    except Exception as e:
        logger.error(f"Error uploading data to cache: {str(e)}")
        return {"code": 500, "message": f"Error uploading data to cache: {str(e)}", "data": None}
