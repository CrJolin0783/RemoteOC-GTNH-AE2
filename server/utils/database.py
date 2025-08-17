import asyncio
import json
import time
from typing import Dict, List, Optional, Any
import sqlite3
import threading
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "ae_network.db"):
        self.db_path = db_path
        self.init_database()
        self.lock = threading.Lock()
    
    def init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建物品表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    label TEXT,
                    damage INTEGER DEFAULT 0,
                    size INTEGER DEFAULT 0,
                    is_craftable BOOLEAN DEFAULT FALSE,
                    tag TEXT,
                    fingerprint TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, label, damage)
                )
            ''')
            
            # 创建CPU表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cpus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    busy BOOLEAN DEFAULT FALSE,
                    coprocessors INTEGER DEFAULT 0,
                    storage INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建客户端状态表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS client_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    known_fingerprints TEXT,
                    sync_count INTEGER DEFAULT 0,
                    UNIQUE(client_id)
                )
            ''')
            
            # 创建流体表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fluids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    label TEXT,
                    amount INTEGER DEFAULT 0,
                    capacity INTEGER DEFAULT 0,
                    tag TEXT,
                    fingerprint TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, label)
                )
            ''')
            
            # 创建存储组件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS storage_components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    stored_items INTEGER DEFAULT 0,
                    stored_fluids INTEGER DEFAULT 0,
                    total_storage INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    fingerprint TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, component_type)
                )
            ''')
            
            # 创建网络统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS network_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL,
                    total_items INTEGER DEFAULT 0,
                    total_fluids INTEGER DEFAULT 0,
                    total_storage INTEGER DEFAULT 0,
                    active_cpus INTEGER DEFAULT 0,
                    network_load REAL DEFAULT 0.0,
                    sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fingerprint TEXT
                )
            ''')
            
            # 创建变更日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS change_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    change_type TEXT NOT NULL,
                    old_data TEXT,
                    new_data TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_items_fingerprint ON items(fingerprint)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fluids_name ON fluids(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fluids_fingerprint ON fluids(fingerprint)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_storage_name ON storage_components(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_network_stats_client ON network_stats(client_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_network_stats_time ON network_stats(sync_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_change_log_time ON change_log(changed_at)')
            
            conn.commit()
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _generate_fingerprint(self, data: Dict) -> str:
        """生成数据指纹"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def upsert_items(self, items: List[Dict]) -> Dict[str, Any]:
        """批量插入或更新物品数据"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            changes = {
                'added': 0,
                'updated': 0,
                'unchanged': 0
            }
            
            for item in items:
                fingerprint = self._generate_fingerprint(item)
                
                # 检查物品是否存在
                cursor.execute('''
                    SELECT fingerprint FROM items 
                    WHERE name = ? AND label = ? AND damage = ?
                ''', (item.get('name', ''), item.get('label', ''), item.get('damage', 0)))
                
                existing = cursor.fetchone()
                
                if existing:
                    if existing[0] != fingerprint:
                        # 更新物品
                        cursor.execute('''
                            UPDATE items SET 
                                size = ?, is_craftable = ?, tag = ?, 
                                fingerprint = ?, last_updated = CURRENT_TIMESTAMP
                            WHERE name = ? AND label = ? AND damage = ?
                        ''', (
                            item.get('size', 0),
                            item.get('isCraftable', False),
                            item.get('tag'),
                            fingerprint,
                            item.get('name', ''),
                            item.get('label', ''),
                            item.get('damage', 0)
                        ))
                        changes['updated'] += 1
                        
                        # 记录变更
                        cursor.execute('''
                            INSERT INTO change_log (table_name, record_id, change_type, old_data, new_data)
                            VALUES (?, ?, ?, ?, ?)
                        ''', ('items', cursor.lastrowid, 'update', existing[0], fingerprint))
                    else:
                        changes['unchanged'] += 1
                else:
                    # 插入新物品
                    cursor.execute('''
                        INSERT INTO items (name, label, damage, size, is_craftable, tag, fingerprint)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('name', ''),
                        item.get('label', ''),
                        item.get('damage', 0),
                        item.get('size', 0),
                        item.get('isCraftable', False),
                        item.get('tag'),
                        fingerprint
                    ))
                    changes['added'] += 1
                    
                    # 记录变更
                    cursor.execute('''
                        INSERT INTO change_log (table_name, record_id, change_type, new_data)
                        VALUES (?, ?, ?, ?)
                    ''', ('items', cursor.lastrowid, 'insert', fingerprint))
            
            conn.commit()
            conn.close()
            return changes
    
    def get_items(self, limit: Optional[int] = None, offset: int = 0, 
                  filters: Optional[Dict] = None) -> List[Dict]:
        """获取物品数据，支持分页和过滤"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT name, label, damage, size, is_craftable, tag, fingerprint FROM items"
            params = []
            
            # 添加过滤条件
            if filters:
                conditions = []
                if filters.get('name'):
                    conditions.append("name LIKE ?")
                    params.append(f"%{filters['name']}%")
                if filters.get('craftable_only'):
                    conditions.append("is_craftable = 1")
                if filters.get('min_size'):
                    conditions.append("size >= ?")
                    params.append(filters['min_size'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY name, label, damage"
            
            # 添加分页
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            items = []
            for row in rows:
                items.append({
                    'name': row[0],
                    'label': row[1],
                    'damage': row[2],
                    'size': row[3],
                    'isCraftable': bool(row[4]),
                    'tag': row[5],
                    'fingerprint': row[6]
                })
            
            conn.close()
            return items
    
    def get_items_count(self, filters: Optional[Dict] = None) -> int:
        """获取物品总数"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM items"
            params = []
            
            if filters:
                conditions = []
                if filters.get('name'):
                    conditions.append("name LIKE ?")
                    params.append(f"%{filters['name']}%")
                if filters.get('craftable_only'):
                    conditions.append("is_craftable = 1")
                if filters.get('min_size'):
                    conditions.append("size >= ?")
                    params.append(filters['min_size'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            conn.close()
            return count
    
    def update_client_state(self, client_id: str, fingerprints: Dict[str, str]):
        """更新客户端同步状态"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO client_states (client_id, known_fingerprints, sync_count)
                VALUES (?, ?, COALESCE((SELECT sync_count FROM client_states WHERE client_id = ?), 0) + 1)
            ''', (client_id, json.dumps(fingerprints), client_id))
            
            conn.commit()
            conn.close()
    
    def get_client_state(self, client_id: str) -> Optional[Dict]:
        """获取客户端同步状态"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_sync, known_fingerprints, sync_count FROM client_states
                WHERE client_id = ?
            ''', (client_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'last_sync': row[0],
                    'known_fingerprints': json.loads(row[1]) if row[1] else {},
                    'sync_count': row[2]
                }
            return None
    
    def get_changes_since(self, timestamp: datetime) -> List[Dict]:
        """获取指定时间后的变更"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT table_name, record_id, change_type, old_data, new_data, changed_at
                FROM change_log
                WHERE changed_at > ?
                ORDER BY changed_at
            ''', (timestamp,))
            
            rows = cursor.fetchall()
            conn.close()
            
            changes = []
            for row in rows:
                changes.append({
                    'table_name': row[0],
                    'record_id': row[1],
                    'change_type': row[2],
                    'old_data': row[3],
                    'new_data': row[4],
                    'changed_at': row[5]
                })
            
            return changes
    
    def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 清理旧的变更日志
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor.execute('''
                DELETE FROM change_log WHERE changed_at < ?
            ''', (cutoff_date,))
            
            # 清理旧的网络统计数据
            cursor.execute('''
                DELETE FROM network_stats WHERE sync_timestamp < ?
            ''', (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old entries")
            return deleted_count
    
    def upsert_fluids(self, fluids: List[Dict]) -> Dict[str, Any]:
        """批量插入或更新流体数据"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            changes = {
                'added': 0,
                'updated': 0,
                'unchanged': 0
            }
            
            for fluid in fluids:
                fingerprint = self._generate_fingerprint(fluid)
                
                # 检查流体是否存在
                cursor.execute('''
                    SELECT fingerprint FROM fluids 
                    WHERE name = ? AND label = ?
                ''', (fluid.get('name', ''), fluid.get('label', '')))
                
                existing = cursor.fetchone()
                
                if existing:
                    if existing[0] != fingerprint:
                        # 更新流体
                        cursor.execute('''
                            UPDATE fluids SET 
                                amount = ?, capacity = ?, tag = ?, 
                                fingerprint = ?, last_updated = CURRENT_TIMESTAMP
                            WHERE name = ? AND label = ?
                        ''', (
                            fluid.get('amount', 0),
                            fluid.get('capacity', 0),
                            fluid.get('tag'),
                            fingerprint,
                            fluid.get('name', ''),
                            fluid.get('label', '')
                        ))
                        changes['updated'] += 1
                        
                        # 记录变更
                        cursor.execute('''
                            INSERT INTO change_log (table_name, record_id, change_type, old_data, new_data)
                            VALUES (?, ?, ?, ?, ?)
                        ''', ('fluids', cursor.lastrowid, 'update', existing[0], fingerprint))
                    else:
                        changes['unchanged'] += 1
                else:
                    # 插入新流体
                    cursor.execute('''
                        INSERT INTO fluids (name, label, amount, capacity, tag, fingerprint)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        fluid.get('name', ''),
                        fluid.get('label', ''),
                        fluid.get('amount', 0),
                        fluid.get('capacity', 0),
                        fluid.get('tag'),
                        fingerprint
                    ))
                    changes['added'] += 1
                    
                    # 记录变更
                    cursor.execute('''
                        INSERT INTO change_log (table_name, record_id, change_type, new_data)
                        VALUES (?, ?, ?, ?)
                    ''', ('fluids', cursor.lastrowid, 'insert', fingerprint))
            
            conn.commit()
            conn.close()
            return changes
    
    def get_fluids(self, limit: Optional[int] = None, offset: int = 0,
                   filters: Optional[Dict] = None) -> List[Dict]:
        """获取流体数据，支持分页和过滤"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT name, label, amount, capacity, tag, fingerprint FROM fluids"
            params = []
            
            # 添加过滤条件
            if filters:
                conditions = []
                if filters.get('name'):
                    conditions.append("name LIKE ?")
                    params.append(f"%{filters['name']}%")
                if filters.get('min_amount'):
                    conditions.append("amount >= ?")
                    params.append(filters['min_amount'])
                if filters.get('has_capacity'):
                    conditions.append("capacity > 0")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY name, label"
            
            # 添加分页
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            fluids = []
            for row in rows:
                fluids.append({
                    'name': row[0],
                    'label': row[1],
                    'amount': row[2],
                    'capacity': row[3],
                    'tag': row[4],
                    'fingerprint': row[5]
                })
            
            conn.close()
            return fluids
    
    def upsert_storage_components(self, components: List[Dict]) -> Dict[str, Any]:
        """批量插入或更新存储组件数据"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            changes = {
                'added': 0,
                'updated': 0,
                'unchanged': 0
            }
            
            for component in components:
                fingerprint = self._generate_fingerprint(component)
                
                # 检查组件是否存在
                cursor.execute('''
                    SELECT fingerprint FROM storage_components 
                    WHERE name = ? AND component_type = ?
                ''', (component.get('name', ''), component.get('component_type', '')))
                
                existing = cursor.fetchone()
                
                if existing:
                    if existing[0] != fingerprint:
                        # 更新组件
                        cursor.execute('''
                            UPDATE storage_components SET 
                                stored_items = ?, stored_fluids = ?, total_storage = ?,
                                is_active = ?, fingerprint = ?, last_updated = CURRENT_TIMESTAMP
                            WHERE name = ? AND component_type = ?
                        ''', (
                            component.get('stored_items', 0),
                            component.get('stored_fluids', 0),
                            component.get('total_storage', 0),
                            component.get('is_active', True),
                            fingerprint,
                            component.get('name', ''),
                            component.get('component_type', '')
                        ))
                        changes['updated'] += 1
                        
                        # 记录变更
                        cursor.execute('''
                            INSERT INTO change_log (table_name, record_id, change_type, old_data, new_data)
                            VALUES (?, ?, ?, ?, ?)
                        ''', ('storage_components', cursor.lastrowid, 'update', existing[0], fingerprint))
                    else:
                        changes['unchanged'] += 1
                else:
                    # 插入新组件
                    cursor.execute('''
                        INSERT INTO storage_components (name, component_type, stored_items, stored_fluids, total_storage, is_active, fingerprint)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        component.get('name', ''),
                        component.get('component_type', ''),
                        component.get('stored_items', 0),
                        component.get('stored_fluids', 0),
                        component.get('total_storage', 0),
                        component.get('is_active', True),
                        fingerprint
                    ))
                    changes['added'] += 1
                    
                    # 记录变更
                    cursor.execute('''
                        INSERT INTO change_log (table_name, record_id, change_type, new_data)
                        VALUES (?, ?, ?, ?)
                    ''', ('storage_components', cursor.lastrowid, 'insert', fingerprint))
            
            conn.commit()
            conn.close()
            return changes
    
    def update_network_stats(self, client_id: str, stats: Dict) -> bool:
        """更新网络统计信息"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            fingerprint = self._generate_fingerprint(stats)
            
            cursor.execute('''
                INSERT INTO network_stats 
                (client_id, total_items, total_fluids, total_storage, active_cpus, network_load, fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_id,
                stats.get('total_items', 0),
                stats.get('total_fluids', 0),
                stats.get('total_storage', 0),
                stats.get('active_cpus', 0),
                stats.get('network_load', 0.0),
                fingerprint
            ))
            
            conn.commit()
            conn.close()
            return True
    
    def get_network_stats(self, client_id: str, limit: int = 100) -> List[Dict]:
        """获取客户端网络统计历史"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT total_items, total_fluids, total_storage, active_cpus, network_load, sync_timestamp
                FROM network_stats
                WHERE client_id = ?
                ORDER BY sync_timestamp DESC
                LIMIT ?
            ''', (client_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            stats = []
            for row in rows:
                stats.append({
                    'total_items': row[0],
                    'total_fluids': row[1],
                    'total_storage': row[2],
                    'active_cpus': row[3],
                    'network_load': row[4],
                    'sync_timestamp': row[5]
                })
            
            return stats
    
    def get_network_summary(self) -> Dict:
        """获取网络整体统计摘要"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取最新的网络统计
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT client_id) as active_clients,
                    AVG(total_items) as avg_items,
                    AVG(total_fluids) as avg_fluids,
                    AVG(total_storage) as avg_storage,
                    AVG(active_cpus) as avg_cpus,
                    AVG(network_load) as avg_load
                FROM network_stats
                WHERE sync_timestamp > datetime('now', '-1 hour')
            ''')
            
            row = cursor.fetchone()
            
            # 获取总数据量
            cursor.execute('SELECT COUNT(*) FROM items')
            total_items = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM fluids')
            total_fluids = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM storage_components')
            total_components = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'active_clients': row[0] if row[0] else 0,
                'avg_items': row[1] if row[1] else 0,
                'avg_fluids': row[2] if row[2] else 0,
                'avg_storage': row[3] if row[3] else 0,
                'avg_cpus': row[4] if row[4] else 0,
                'avg_load': row[5] if row[5] else 0.0,
                'total_items': total_items,
                'total_fluids': total_fluids,
                'total_components': total_components
            }
    
    def get_data_changes_since(self, timestamp: datetime) -> Dict:
        """获取指定时间后的所有数据变更"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            changes = {
                'items': [],
                'fluids': [],
                'storage_components': [],
                'network_stats': []
            }
            
            # 获取变更的物品
            cursor.execute('''
                SELECT name, label, damage, size, is_craftable, tag, fingerprint, last_updated
                FROM items
                WHERE last_updated > ?
                ORDER BY last_updated
            ''', (timestamp,))
            
            for row in cursor.fetchall():
                changes['items'].append({
                    'name': row[0], 'label': row[1], 'damage': row[2],
                    'size': row[3], 'isCraftable': bool(row[4]), 'tag': row[5],
                    'fingerprint': row[6], 'last_updated': row[7]
                })
            
            # 获取变更的流体
            cursor.execute('''
                SELECT name, label, amount, capacity, tag, fingerprint, last_updated
                FROM fluids
                WHERE last_updated > ?
                ORDER BY last_updated
            ''', (timestamp,))
            
            for row in cursor.fetchall():
                changes['fluids'].append({
                    'name': row[0], 'label': row[1], 'amount': row[2],
                    'capacity': row[3], 'tag': row[4], 'fingerprint': row[5],
                    'last_updated': row[6]
                })
            
            conn.close()
            return changes

db_manager = DatabaseManager()