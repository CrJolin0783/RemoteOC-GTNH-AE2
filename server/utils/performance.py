import time
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DeduplicationManager:
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.recent_requests = []
        self.request_hashes = {}
        self.response_cache = {}
        self.lock = asyncio.Lock()
    
    async def _generate_request_hash(self, request_data: Dict) -> str:
        """生成请求哈希用于去重"""
        import hashlib
        request_str = json.dumps(request_data, sort_keys=True)
        return hashlib.md5(request_str.encode()).hexdigest()
    
    async def is_duplicate_request(self, request_data: Dict, timeout: int = 60) -> bool:
        """检查是否为重复请求"""
        async with self.lock:
            request_hash = await self._generate_request_hash(request_data)
            current_time = time.time()
            
            # 清理过期的请求记录
            self.recent_requests = [
                req_time for req_time in self.recent_requests 
                if current_time - req_time < timeout
            ]
            
            # 检查是否在窗口期内有相同请求
            if request_hash in self.request_hashes:
                last_time = self.request_hashes[request_hash]
                if current_time - last_time < timeout:
                    return True
            
            # 记录新请求
            self.recent_requests.append(current_time)
            self.request_hashes[request_hash] = current_time
            
            return False
    
    async def cache_response(self, request_hash: str, response_data: Any, ttl: int = 300):
        """缓存响应数据"""
        async with self.lock:
            self.response_cache[request_hash] = {
                'data': response_data,
                'expires_at': time.time() + ttl
            }
    
    async def get_cached_response(self, request_hash: str) -> Optional[Any]:
        """获取缓存的响应"""
        async with self.lock:
            if request_hash in self.response_cache:
                cache_entry = self.response_cache[request_hash]
                if time.time() < cache_entry['expires_at']:
                    return cache_entry['data']
                else:
                    del self.response_cache[request_hash]
            return None
    
    async def cleanup_expired_cache(self):
        """清理过期缓存"""
        async with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.response_cache.items()
                if current_time >= entry['expires_at']
            ]
            
            for key in expired_keys:
                del self.response_cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

class QueueManager:
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.request_queue = asyncio.Queue()
        self.active_requests = 0
        self.processing_task = None
        self.stats = {
            'total_requests': 0,
            'completed_requests': 0,
            'failed_requests': 0,
            'average_processing_time': 0
        }
    
    async def add_request(self, request_data: Dict, priority: int = 0) -> str:
        """添加请求到队列"""
        request_id = f"req_{int(time.time() * 1000)}_{self.stats['total_requests']}"
        queue_item = {
            'id': request_id,
            'data': request_data,
            'priority': priority,
            'created_at': time.time(),
            'status': 'queued'
        }
        
        await self.request_queue.put(queue_item)
        self.stats['total_requests'] += 1
        
        # 启动处理任务（如果未运行）
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_queue())
        
        logger.debug(f"Added request {request_id} to queue with priority {priority}")
        return request_id
    
    async def _process_queue(self):
        """处理队列中的请求"""
        while True:
            try:
                if self.active_requests < self.max_concurrent:
                    # 从队列中获取请求
                    queue_item = await asyncio.wait_for(
                        self.request_queue.get(), 
                        timeout=1.0
                    )
                    
                    self.active_requests += 1
                    queue_item['status'] = 'processing'
                    queue_item['started_at'] = time.time()
                    
                    # 创建处理任务
                    asyncio.create_task(self._process_request(queue_item))
                else:
                    await asyncio.sleep(0.1)
                    
            except asyncio.TimeoutError:
                # 队列为空，等待新请求
                continue
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                await asyncio.sleep(1)
    
    async def _process_request(self, queue_item: Dict):
        """处理单个请求"""
        request_id = queue_item['id']
        start_time = time.time()
        
        try:
            # 这里应该调用实际的处理逻辑
            # 由于这是一个框架，我们模拟处理过程
            await asyncio.sleep(0.1)  # 模拟处理时间
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_stats(processing_time, success=True)
            
            queue_item['status'] = 'completed'
            queue_item['completed_at'] = time.time()
            
            logger.debug(f"Completed request {request_id} in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing request {request_id}: {e}")
            self._update_stats(0, success=False)
            
            queue_item['status'] = 'failed'
            queue_item['error'] = str(e)
            queue_item['completed_at'] = time.time()
        
        finally:
            self.active_requests -= 1
            self.request_queue.task_done()
    
    def _update_stats(self, processing_time: float, success: bool):
        """更新统计信息"""
        if success:
            self.stats['completed_requests'] += 1
            
            # 更新平均处理时间
            total = self.stats['completed_requests']
            current_avg = self.stats['average_processing_time']
            self.stats['average_processing_time'] = (
                (current_avg * (total - 1) + processing_time) / total
            )
        else:
            self.stats['failed_requests'] += 1
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            'queue_size': self.request_queue.qsize(),
            'active_requests': self.active_requests,
            'max_concurrent': self.max_concurrent,
            'stats': self.stats.copy()
        }

class PerformanceOptimizer:
    """性能优化器主类"""
    
    def __init__(self):
        self.dedup_manager = DeduplicationManager()
        self.queue_manager = QueueManager()
        self.cleanup_task = None
    
    async def initialize(self):
        """初始化优化器"""
        # 启动定期清理任务
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info("Performance optimizer initialized")
    
    async def process_request(self, request_data: Dict) -> Dict[str, Any]:
        """处理请求，包含去重、队列化等优化"""
        # 检查重复请求
        if await self.dedup_manager.is_duplicate_request(request_data):
            logger.warning(f"Duplicate request detected: {request_data}")
            return {'error': 'Duplicate request', 'code': 429}
        
        # 生成请求哈希
        request_hash = await self.dedup_manager._generate_request_hash(request_data)
        
        # 检查缓存
        cached_response = await self.dedup_manager.get_cached_response(request_hash)
        if cached_response:
            logger.debug(f"Cache hit for request: {request_hash}")
            return cached_response
        
        # 添加到队列
        request_id = await self.queue_manager.add_request(request_data)
        
        # 返回请求ID，客户端可以轮询结果
        return {
            'request_id': request_id,
            'status': 'queued',
            'message': 'Request added to processing queue'
        }
    
    async def _periodic_cleanup(self):
        """定期清理任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self.dedup_manager.cleanup_expired_cache()
                logger.debug("Periodic cleanup completed")
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return {
            'queue_status': await self.queue_manager.get_queue_status(),
            'cache_size': len(self.dedup_manager.response_cache),
            'recent_requests': len(self.dedup_manager.recent_requests)
        }

# 全局实例
performance_optimizer = PerformanceOptimizer()