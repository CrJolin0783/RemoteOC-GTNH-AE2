from config import SERVER_TOKEN
from utils.database import db_manager
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from models import *
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def token_required(x_server_token: str = Header(...)):
    """Token 验证依赖"""
    if x_server_token != SERVER_TOKEN:
        raise HTTPException(status_code=403, detail="Unauthorized, invalid token")


@router.get("/summary", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_network_summary():
    """获取网络整体统计摘要"""
    try:
        summary = db_manager.get_network_summary()
        return StandardResponseModel(
            code=200,
            message="获取网络统计摘要成功",
            data=summary
        )
    except Exception as e:
        logger.error(f"Error getting network summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_items(
    limit: Optional[int] = Query(100, description="限制返回数量"),
    offset: int = Query(0, description="偏移量"),
    name: Optional[str] = Query(None, description="物品名称过滤"),
    craftable_only: bool = Query(False, description="仅显示可合成物品"),
    min_size: int = Query(0, description="最小数量")
):
    """获取物品数据，支持分页和过滤"""
    try:
        filters = {}
        if name:
            filters['name'] = name
        if craftable_only:
            filters['craftable_only'] = True
        if min_size > 0:
            filters['min_size'] = min_size
        
        items = db_manager.get_items(limit=limit, offset=offset, filters=filters)
        total = db_manager.get_items_count(filters=filters)
        
        return StandardResponseModel(
            code=200,
            message="获取物品数据成功",
            data={
                'items': items,
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total
            }
        )
    except Exception as e:
        logger.error(f"Error getting items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fluids", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_fluids(
    limit: Optional[int] = Query(100, description="限制返回数量"),
    offset: int = Query(0, description="偏移量"),
    name: Optional[str] = Query(None, description="流体名称过滤"),
    min_amount: int = Query(0, description="最小数量"),
    has_capacity: bool = Query(False, description="仅显示有容量的流体")
):
    """获取流体数据，支持分页和过滤"""
    try:
        filters = {}
        if name:
            filters['name'] = name
        if min_amount > 0:
            filters['min_amount'] = min_amount
        if has_capacity:
            filters['has_capacity'] = True
        
        fluids = db_manager.get_fluids(limit=limit, offset=offset, filters=filters)
        
        return StandardResponseModel(
            code=200,
            message="获取流体数据成功",
            data={
                'fluids': fluids,
                'limit': limit,
                'offset': offset
            }
        )
    except Exception as e:
        logger.error(f"Error getting fluids: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_client_stats(
    client_id: str = Query(..., description="客户端ID"),
    limit: int = Query(100, description="返回记录数量")
):
    """获取客户端网络统计历史"""
    try:
        stats = db_manager.get_network_stats(client_id, limit)
        return StandardResponseModel(
            code=200,
            message="获取客户端统计成功",
            data={
                'client_id': client_id,
                'stats': stats,
                'count': len(stats)
            }
        )
    except Exception as e:
        logger.error(f"Error getting client stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_data_changes(
    timestamp: Optional[str] = Query(None, description="时间戳 (ISO格式)"),
    minutes_ago: int = Query(5, description="几分钟前的数据 (默认5分钟)")
):
    """获取指定时间后的数据变更"""
    try:
        if timestamp:
            try:
                cutoff_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
        else:
            cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
        
        changes = db_manager.get_data_changes_since(cutoff_time)
        
        return StandardResponseModel(
            code=200,
            message="获取数据变更成功",
            data={
                'changes': changes,
                'cutoff_time': cutoff_time.isoformat(),
                'total_changes': sum(len(v) for v in changes.values())
            }
        )
    except Exception as e:
        logger.error(f"Error getting data changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def cleanup_old_data(
    days: int = Query(30, description="清理多少天前的数据")
):
    """清理旧数据"""
    try:
        deleted_count = db_manager.cleanup_old_data(days)
        return StandardResponseModel(
            code=200,
            message=f"清理完成，删除了 {deleted_count} 条记录",
            data={'deleted_count': deleted_count, 'days': days}
        )
    except Exception as e:
        logger.error(f"Error cleaning up data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client-state", response_model=StandardResponseModel, dependencies=[Depends(token_required)])
async def get_client_state(
    client_id: str = Query(..., description="客户端ID")
):
    """获取客户端同步状态"""
    try:
        state = db_manager.get_client_state(client_id)
        if state:
            return StandardResponseModel(
                code=200,
                message="获取客户端状态成功",
                data=state
            )
        else:
            return StandardResponseModel(
                code=404,
                message="客户端状态不存在",
                data=None
            )
    except Exception as e:
        logger.error(f"Error getting client state: {e}")
        raise HTTPException(status_code=500, detail=str(e))