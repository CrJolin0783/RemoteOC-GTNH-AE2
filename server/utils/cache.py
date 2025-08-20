import asyncio
import json
import time
from typing import Dict, List, Optional, Any
import hashlib
import logging
from datetime import datetime, timedelta

try:
    import redis
    import msgpack
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class IntelligentCache:
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: Dict[str, Dict] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times: Dict[str, float] = {}
        self.change_tracking: Dict[str, str] = {}
    
    def _generate_fingerprint(self, data: Any) -> str:
        """生成数据指纹用于变更检测"""
        if isinstance(data, (list, dict)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _is_expired(self, cache_entry: Dict) -> bool:
        """检查缓存是否过期"""
        if 'expires_at' not in cache_entry:
            return True
        return datetime.now() > cache_entry['expires_at']
    
    def _evict_if_needed(self):
        """LRU缓存淘汰"""
        if len(self.cache) <= self.max_size:
            return
        
        sorted_items = sorted(
            self.access_times.items(), 
            key=lambda x: x[1]
        )
        
        for key, _ in sorted_items[:len(self.cache) - self.max_size]:
            self.remove(key)
    
    def get(self, key: str) -> Optional[Dict]:
        """获取缓存数据"""
        if key not in self.cache:
            return None
        
        cache_entry = self.cache[key]
        
        if self._is_expired(cache_entry):
            self.remove(key)
            return None
        
        self.access_times[key] = time.time()
        return {
            'data': cache_entry['data'],
            'fingerprint': cache_entry.get('fingerprint'),
            'cached_at': cache_entry['created_at']
        }
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> str:
        """设置缓存数据"""
        fingerprint = self._generate_fingerprint(data)
        
        existing_cache = self.get(key)
        if existing_cache and existing_cache['fingerprint'] == fingerprint:
            logger.debug(f"Data unchanged for key: {key}")
            return fingerprint
        
        cache_entry = {
            'data': data,
            'fingerprint': fingerprint,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        }
        
        self.cache[key] = cache_entry
        self.access_times[key] = time.time()
        
        old_fingerprint = self.change_tracking.get(key)
        self.change_tracking[key] = fingerprint
        
        self._evict_if_needed()
        
        if old_fingerprint and old_fingerprint != fingerprint:
            logger.info(f"Data changed for key: {key}")
            return 'changed'
        
        return fingerprint
    
    def remove(self, key: str):
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
        if key in self.change_tracking:
            del self.change_tracking[key]
    
    def get_changes_since(self, timestamp: datetime) -> Dict[str, Any]:
        """获取指定时间后的变更"""
        changes = {}
        for key, fingerprint in self.change_tracking.items():
            if key in self.cache:
                cache_entry = self.cache[key]
                if cache_entry['created_at'] > timestamp:
                    changes[key] = {
                        'data': cache_entry['data'],
                        'fingerprint': fingerprint,
                        'changed_at': cache_entry['created_at']
                    }
        return changes
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()
        self.change_tracking.clear()
    
    def stats(self) -> Dict[str, Any]:
        """缓存统计信息"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'expired_count': sum(1 for entry in self.cache.values() if self._is_expired(entry)),
            'keys': list(self.cache.keys())
        }

cache = IntelligentCache()

class IncrementalSyncManager:
    def __init__(self):
        self.client_states: Dict[str, Dict[str, Any]] = {}
        self.last_full_sync: Dict[str, datetime] = {}
    
    def get_client_state(self, client_id: str) -> Dict[str, Any]:
        """获取客户端同步状态"""
        if client_id not in self.client_states:
            self.client_states[client_id] = {
                'last_sync': datetime.now(),
                'known_fingerprints': {},
                'sync_count': 0
            }
        return self.client_states[client_id]
    
    def should_full_sync(self, client_id: str, force: bool = False) -> bool:
        """判断是否需要全量同步"""
        state = self.get_client_state(client_id)
        
        if force:
            return True
        
        if client_id not in self.last_full_sync:
            return True
        
        time_since_full = datetime.now() - self.last_full_sync[client_id]
        return time_since_full > timedelta(minutes=30)
    
    def get_incremental_update(self, client_id: str, data_type: str) -> Dict[str, Any]:
        """获取增量更新"""
        state = self.get_client_state(client_id)
        cache_key = f"{client_id}_{data_type}"
        
        cached_data = cache.get(cache_key)
        if not cached_data:
            return {'type': 'full_sync', 'data': None}
        
        current_fingerprint = cached_data['fingerprint']
        known_fingerprint = state['known_fingerprints'].get(data_type)
        
        if known_fingerprint != current_fingerprint or self.should_full_sync(client_id):
            state['known_fingerprints'][data_type] = current_fingerprint
            state['last_sync'] = datetime.now()
            self.last_full_sync[client_id] = datetime.now()
            state['sync_count'] += 1
            
            return {
                'type': 'full_sync',
                'data': cached_data['data'],
                'fingerprint': current_fingerprint,
                'sync_count': state['sync_count']
            }
        
        return {
            'type': 'no_change',
            'fingerprint': current_fingerprint
        }
    
    def update_data(self, client_id: str, data_type: str, data: Any) -> Dict[str, Any]:
        """更新数据并返回变更信息"""
        cache_key = f"{client_id}_{data_type}"
        result = cache.set(cache_key, data)
        
        return {
            'type': 'update_result',
            'cache_key': cache_key,
            'fingerprint': result,
            'changed': result == 'changed'
        }

class RedisCache:
    def __init__(self, redis_url: str = "redis://localhost:6379/0", default_ttl: int = 300):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_client = None
        self.connected = False
        
        if REDIS_AVAILABLE:
            self._connect()
        else:
            logger.warning("Redis not available, falling back to memory cache")
    
    def _connect(self):
        """连接到Redis服务器"""
        if not REDIS_AVAILABLE:
            return
            
        # 尝试连接Redis，最多重试5次
        for attempt in range(5):
            try:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
                # 测试连接
                self.redis_client.ping()
                self.connected = True
                logger.info(f"Connected to Redis at {self.redis_url}")
                return
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to connect to Redis: {e}")
                if attempt < 4:  # 不是最后一次尝试，等待一段时间再重试
                    import time
                    time.sleep(3)  # 增加等待时间到3秒
                else:
                    logger.error(f"Failed to connect to Redis after 5 attempts: {e}")
                    self.connected = False
    
    def _serialize(self, data: Any) -> bytes:
        """使用MessagePack序列化数据"""
        if REDIS_AVAILABLE:
            return msgpack.packb(data, use_bin_type=True)
        else:
            return json.dumps(data).encode('utf-8')
    
    def _deserialize(self, data: bytes) -> Any:
        """使用MessagePack反序列化数据"""
        if not data:
            return None
            
        if REDIS_AVAILABLE:
            try:
                return msgpack.unpackb(data, raw=False)
            except:
                # 如果MessagePack失败，尝试JSON
                return json.loads(data.decode('utf-8'))
        else:
            return json.loads(data.decode('utf-8'))
    
    def _generate_fingerprint(self, data: Any) -> str:
        """生成数据指纹用于变更检测"""
        if isinstance(data, (list, dict)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Dict]:
        """从Redis获取缓存数据"""
        if not self.connected:
            return None
            
        try:
            data = self.redis_client.get(f"cache:{key}")
            if data:
                cache_entry = self._deserialize(data)
                
                # 检查是否过期
                expires_at = cache_entry.get('expires_at')
                if expires_at and datetime.now().timestamp() > expires_at:
                    self.remove(key)
                    return None
                
                # 更新访问时间
                self.redis_client.expire(f"cache:{key}", self.default_ttl)
                
                return {
                    'data': cache_entry['data'],
                    'fingerprint': cache_entry.get('fingerprint'),
                    'cached_at': datetime.fromtimestamp(cache_entry['created_at'])
                }
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
        
        return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> str:
        """设置Redis缓存数据"""
        if not self.connected:
            return None
            
        try:
            fingerprint = self._generate_fingerprint(data)
            now = datetime.now()
            
            # 检查数据是否变化
            existing_cache = self.get(key)
            if existing_cache and existing_cache['fingerprint'] == fingerprint:
                logger.debug(f"Data unchanged for key: {key}")
                return fingerprint
            
            cache_entry = {
                'data': data,
                'fingerprint': fingerprint,
                'created_at': now.timestamp(),
                'expires_at': (now + timedelta(seconds=ttl or self.default_ttl)).timestamp()
            }
            
            serialized_data = self._serialize(cache_entry)
            cache_key = f"cache:{key}"
            
            # 设置缓存
            self.redis_client.setex(cache_key, ttl or self.default_ttl, serialized_data)
            
            # 记录变更历史
            change_key = f"change:{key}"
            self.redis_client.setex(change_key, 86400, fingerprint)  # 变更记录保存24小时
            
            # 检查是否为变更
            old_fingerprint = None
            if existing_cache:
                old_fingerprint = existing_cache['fingerprint']
            
            if old_fingerprint and old_fingerprint != fingerprint:
                logger.info(f"Data changed for key: {key}")
                return 'changed'
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return None
    
    def remove(self, key: str):
        """从Redis删除缓存"""
        if not self.connected:
            return
            
        try:
            self.redis_client.delete(f"cache:{key}")
            self.redis_client.delete(f"change:{key}")
        except Exception as e:
            logger.error(f"Error removing cache for key {key}: {e}")
    
    def get_changes_since(self, timestamp: datetime) -> Dict[str, Any]:
        """获取指定时间后的变更"""
        if not self.connected:
            return {}
            
        changes = {}
        try:
            # 获取所有变更键
            change_keys = self.redis_client.keys("change:*")
            
            for change_key in change_keys:
                key = change_key.decode('utf-8').replace("change:", "")
                fingerprint = self.redis_client.get(change_key)
                
                if fingerprint:
                    cache_data = self.get(key)
                    if cache_data and cache_data['cached_at'] > timestamp:
                        changes[key] = {
                            'data': cache_data['data'],
                            'fingerprint': fingerprint.decode('utf-8'),
                            'changed_at': cache_data['cached_at']
                        }
        except Exception as e:
            logger.error(f"Error getting changes since {timestamp}: {e}")
        
        return changes
    
    def clear(self):
        """清空Redis缓存"""
        if not self.connected:
            return
            
        try:
            # 只清除我们的缓存键，不清空整个Redis
            cache_keys = self.redis_client.keys("cache:*")
            change_keys = self.redis_client.keys("change:*")
            
            if cache_keys:
                self.redis_client.delete(*cache_keys)
            if change_keys:
                self.redis_client.delete(*change_keys)
                
            logger.info("Cleared all cache entries")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def stats(self) -> Dict[str, Any]:
        """Redis缓存统计信息"""
        stats = {
            'connected': self.connected,
            'redis_url': self.redis_url,
            'size': 0
        }
        
        if self.connected:
            try:
                cache_keys = self.redis_client.keys("cache:*")
                stats['size'] = len(cache_keys)
                stats['keys'] = [key.decode('utf-8').replace("cache:", "") for key in cache_keys]
                
                # 获取Redis信息
                info = self.redis_client.info()
                stats['redis_info'] = {
                    'used_memory': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 'N/A'),
                    'total_commands_processed': info.get('total_commands_processed', 'N/A')
                }
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return stats

class DistributedCacheManager:
    """分布式缓存管理器，支持Redis和内存缓存"""
    def __init__(self, redis_url: str = "redis://localhost:6379/0", use_redis: bool = True):
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.redis_cache = None
        self.memory_cache = IntelligentCache()
        
        if self.use_redis:
            self.redis_cache = RedisCache(redis_url)
            if not self.redis_cache.connected:
                logger.warning("Redis connection failed, falling back to memory cache")
                self.use_redis = False
    
    def get(self, key: str) -> Optional[Dict]:
        """获取缓存数据"""
        if self.use_redis and self.redis_cache:
            return self.redis_cache.get(key)
        else:
            return self.memory_cache.get(key)
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> str:
        """设置缓存数据"""
        if self.use_redis and self.redis_cache:
            return self.redis_cache.set(key, data, ttl)
        else:
            return self.memory_cache.set(key, data, ttl)
    
    def remove(self, key: str):
        """删除缓存"""
        if self.use_redis and self.redis_cache:
            self.redis_cache.remove(key)
        else:
            self.memory_cache.remove(key)
    
    def get_changes_since(self, timestamp: datetime) -> Dict[str, Any]:
        """获取指定时间后的变更"""
        if self.use_redis and self.redis_cache:
            return self.redis_cache.get_changes_since(timestamp)
        else:
            return self.memory_cache.get_changes_since(timestamp)
    
    def clear(self):
        """清空缓存"""
        if self.use_redis and self.redis_cache:
            self.redis_cache.clear()
        else:
            self.memory_cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """缓存统计信息"""
        if self.use_redis and self.redis_cache:
            return self.redis_cache.stats()
        else:
            return self.memory_cache.stats()

# 创建全局缓存实例
try:
    # 从环境变量获取Redis配置
    import os
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    use_redis = os.getenv('USE_REDIS', 'true').lower() == 'true'
    
    distributed_cache = DistributedCacheManager(redis_url, use_redis)
    logger.info(f"Initialized distributed cache (Redis: {use_redis})")
except Exception as e:
    logger.error(f"Error initializing distributed cache: {e}")
    distributed_cache = DistributedCacheManager(use_redis=False)

# 保留原有的缓存实例用于向后兼容
cache = IntelligentCache()
incremental_sync = IncrementalSyncManager()