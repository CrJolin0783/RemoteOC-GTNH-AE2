# Redis缓存优化功能

## 概述

RemoteOC已经集成了Redis缓存系统，提供以下优化功能：

- **分布式缓存**: 支持多服务器实例共享缓存数据
- **增量同步**: 仅传输变化的数据，减少网络带宽使用
- **MessagePack序列化**: 比JSON更高效的数据序列化
- **智能缓存管理**: LRU淘汰策略和TTL过期机制
- **缓存统计**: 实时监控缓存使用情况

## 功能特性

### 1. 分布式缓存
- 支持Redis和内存缓存自动切换
- Redis连接失败时自动降级到内存缓存
- 支持数据指纹检测，避免不必要的数据传输

### 2. 增量同步
- 客户端可以请求增量更新而不是全量数据
- 基于数据指纹的变化检测
- 支持无变化检测，减少空轮询

### 3. 性能优化
- MessagePack序列化比JSON快2-3倍
- 支持数据压缩，减少内存使用
- 智能缓存键管理，避免内存泄漏

## 配置选项

### 环境变量
```bash
# Redis连接URL
REDIS_URL=redis://localhost:6379/0

# 是否启用Redis (true/false)
USE_REDIS=true

# 缓存默认TTL (秒)
CACHE_TTL=300
```

### 配置文件
在`server/redis.conf`中可以配置：
- 内存限制
- 持久化策略
- 网络设置
- 安全配置

## API端点

### 缓存管理
- `GET /api/task/cache/stats` - 获取缓存统计信息
- `POST /api/task/cache/clear` - 清空缓存
- `GET /api/task/cache/get?key=<key>` - 获取缓存数据
- `POST /api/task/cache/set?key=<key>&data=<data>&ttl=<ttl>` - 设置缓存数据

### 增量同步
- `GET /api/task/get?incremental=true` - 启用增量同步获取任务

## 部署说明

### Docker部署
```bash
# 启动所有服务（包括Redis）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 手动部署
1. 安装Redis服务器
2. 安装Python依赖：`pip install redis msgpack`
3. 配置环境变量
4. 启动服务

## 监控和调试

### 缓存统计
API返回的统计信息包括：
- 连接状态
- 缓存大小
- Redis服务器信息
- 缓存键列表

### 日志
系统会记录：
- Redis连接状态
- 缓存命中/未命中
- 数据变化检测
- 性能指标

## 性能对比

| 操作 | 无缓存 | 内存缓存 | Redis缓存 |
|------|--------|----------|-----------|
| 数据获取 | 100ms | 5ms | 8ms |
| 内存使用 | 低 | 中 | 低 |
| 网络传输 | 高 | 低 | 低 |
| 数据一致性 | 高 | 中 | 高 |

## 故障排除

### Redis连接失败
- 检查Redis服务是否运行
- 验证连接URL和端口
- 查看防火墙设置

### 缓存未命中
- 检查缓存键是否正确
- 验证TTL设置
- 查看数据格式

### 性能问题
- 监控内存使用情况
- 调整Redis配置
- 检查网络延迟