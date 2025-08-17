import msgpack
import zlib
import json
import base64
from typing import Any, Union, Dict, List
import logging

logger = logging.getLogger(__name__)

class MessagePackSerializer:
    """高性能数据序列化器"""
    
    @staticmethod
    def serialize(data: Any, compress: bool = True) -> bytes:
        """序列化数据为字节"""
        try:
            packed = msgpack.packb(data, use_bin_type=True)
            if compress:
                packed = zlib.compress(packed, level=zlib.Z_BEST_COMPRESSION)
            return packed
        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            return json.dumps(data).encode()
    
    @staticmethod
    def deserialize(data: bytes, compressed: bool = True) -> Any:
        """反序列化数据"""
        try:
            if compressed:
                data = zlib.decompress(data)
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            return json.loads(data.decode())

class DataOptimizer:
    """数据优化器，用于减少数据传输量"""
    
    @staticmethod
    def optimize_item_data(items: List[Dict]) -> List[Dict]:
        """优化物品数据"""
        optimized = []
        
        for item in items:
            optimized_item = {
                'n': item.get('name', ''),
                'l': item.get('label', ''),
                'd': item.get('damage', 0),
                's': item.get('size', 0) or item.get('amount', 0),
                'c': item.get('isCraftable', False)
            }
            
            if 'tag' in item and item['tag']:
                optimized_item['t'] = item['tag']
            
            optimized.append(optimized_item)
        
        return optimized
    
    @staticmethod
    def optimize_cpu_data(cpus: List[Dict]) -> List[Dict]:
        """优化CPU数据"""
        optimized = []
        
        for cpu in cpus:
            optimized_cpu = {
                'n': cpu.get('name', ''),
                'b': cpu.get('busy', False),
                'c': cpu.get('coprocessors', 0),
                's': cpu.get('storage', 0)
            }
            
            if 'cpu' in cpu:
                cpu_detail = cpu['cpu']
                optimized_cpu['d'] = {
                    'a': cpu_detail.get('active', False),
                    'b': cpu_detail.get('busy', False),
                    'fo': cpu_detail.get('finalOutput'),
                    'ai': cpu_detail.get('activeItems', []),
                    'pi': cpu_detail.get('pendingItems', []),
                    'si': cpu_detail.get('storedItems', [])
                }
            
            optimized.append(optimized_cpu)
        
        return optimized
    
    @staticmethod
    def create_delta_patch(old_data: List[Dict], new_data: List[Dict], key_field: str = 'name') -> Dict:
        """创建增量补丁"""
        old_dict = {item[key_field]: item for item in old_data}
        new_dict = {item[key_field]: item for item in new_data}
        
        added = []
        modified = []
        removed = []
        
        for key, new_item in new_dict.items():
            if key not in old_dict:
                added.append(new_item)
            elif old_dict[key] != new_item:
                modified.append(new_item)
        
        for key in old_dict:
            if key not in new_dict:
                removed.append(key)
        
        return {
            'added': added,
            'modified': modified,
            'removed': removed,
            'timestamp': new_data[-1].get('timestamp') if new_data else None
        }

class RequestBatcher:
    """请求批处理器"""
    
    def __init__(self, max_batch_size: int = 100, max_wait_time: float = 1.0):
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        self.pending_requests = []
        self.last_batch_time = 0
    
    def add_request(self, request: Dict) -> bool:
        """添加请求到批处理队列"""
        self.pending_requests.append(request)
        
        current_time = time.time()
        if (len(self.pending_requests) >= self.max_batch_size or 
            current_time - self.last_batch_time >= self.max_wait_time):
            return self.flush_batch()
        
        return False
    
    def flush_batch(self) -> List[Dict]:
        """刷新批处理队列"""
        if not self.pending_requests:
            return []
        
        batch = self.pending_requests.copy()
        self.pending_requests.clear()
        self.last_batch_time = time.time()
        
        return batch

serializer = MessagePackSerializer()
optimizer = DataOptimizer()
batcher = RequestBatcher()