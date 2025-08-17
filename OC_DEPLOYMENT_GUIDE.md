# OpenComputers客户端部署指南

## 硬件要求

### 基础配置
- **T3 CPU** 或更高 (推荐T3.5/T4)
- **内存**: 4GB+ (推荐8GB)
- **硬盘**: 16GB+ (推荐32GB)
- **网络卡**: T1+ 网络卡 (支持HTTP请求)
- **电源**: 稳定电源供应

### 可选组件
- **显示器**: 用于调试和监控
- **键盘**: 用于本地操作
- **红石卡**: 用于与其他设备交互

## 软件要求

### OpenComputers组件
- OpenComputers模组 (GTNH AE2版本)
- Lua 5.2+ (OpenComputers内置)
- 支持HTTP请求的库

### 网络环境
- 能够访问服务器的网络连接
- 确保游戏服务器允许HTTP出站连接

## 部署步骤

### 1. 硬件安装
```
1. 放置电脑机箱
2. 安装CPU、内存、硬盘
3. 安装网络卡
4. 连接电源
5. 启动电脑
```

### 2. 系统安装
```lua
-- 在电脑终端中执行
install
```

### 3. 网络配置
```lua
-- 测试网络连接
ping "8.8.8.8"

-- 检查HTTP功能
local component = require("component")
local internet = component.internet
```

### 4. 客户端文件上传
将以下文件上传到OpenComputers电脑：

#### 必需文件
- `run.lua` - 主程序
- `env.lua` - 配置文件
- `src/` 目录及其内容
- `plugins/` 目录及其内容

#### 上传方法
```lua
-- 使用OpenOS的文件系统API
local fs = require("filesystem")
local shell = require("shell")

-- 创建目录结构
shell.makeDirectory("src")
shell.makeDirectory("plugins")
```

## 配置文件设置

### 编辑env.lua
```lua
local env = {
    -- 轮询间隔时间（秒）
    pollingInterval = 8,

    -- 服务器地址
    baseUrl = "http://your-server-ip:26766",

    -- 客户端ID（多客户端时需要唯一）
    clientId = "client_01",

    -- 服务器令牌（必须与服务器配置一致）
    serverToken = "3d4ed77e60b1aac9c7e4ca7f3a5cb47b",

    -- AE2控制器地址（自动检测或手动设置）
    aeAddress = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",

    -- 分块上传大小
    chunkSize = 256,

    -- API路径
    getPath = "/api/task/get",
    reportPath = "/api/task/report",
    chunkedReportPath = "/api/task/chunked_report",
}
```

### AE2地址配置
```lua
-- 自动检测AE2设备
local component = require("component")
local aeController = component.me_controller or component.me_interface

if aeController then
    print("AE2设备地址:", aeController.address)
    env.aeAddress = aeController.address
end
```

## 启动客户端

### 手动启动
```lua
-- 在OpenComputers终端中执行
run
```

### 自动启动
将以下内容添加到 `/autorun.lua`:
```lua
-- 自动启动客户端
local function startClient()
    local success, reason = pcall(loadfile("run.lua"))
    if not success then
        print("启动失败:", reason)
    end
end

startClient()
```

## AE2系统连接

### ME控制器连接
1. 将ME控制器与ME网络连接
2. 确保ME网络正常工作
3. 使用适配器块连接到电脑

### ME接口连接
1. 将ME接口连接到ME网络
2. 使用适配器块连接到电脑
3. 配置接口访问权限

### 网络测试
```lua
-- 测试AE2连接
local component = require("component")
local ae = component.me_controller or component.me_interface

if ae then
    print("AE2连接成功")
    print("物品数量:", ae.getTotalItemStorage())
    print("流体数量:", ae.getTotalFluidStorage())
else
    print("AE2连接失败")
end
```

## 监控和调试

### 系统监控
```lua
-- 查看系统状态
local computer = require("computer")
print("CPU使用率:", computer.cpuUsage() .. "%")
print("内存使用:", computer.freeMemory() .. "/" .. computer.totalMemory())
print("运行时间:", computer.uptime() .. "秒")
```

### 网络测试
```lua
-- 测试服务器连接
local internet = require("internet")
local function testConnection()
    local success, data = pcall(internet.request, env.baseUrl .. "/api/task/get", nil, {
        ["X-Server-Token"] = env.serverToken
    })
    if success then
        print("服务器连接正常")
    else
        print("服务器连接失败:", data)
    end
end
```

### 日志查看
```lua
-- 查看客户端日志
local fs = require("filesystem")
local file = io.open("client.log", "r")
if file then
    print(file:read("*all"))
    file:close()
end
```

## 故障排除

### 常见问题

#### 1. 网络连接问题
- 检查网络卡是否正确安装
- 确认服务器地址和端口正确
- 检查防火墙设置

#### 2. AE2连接问题
- 确认ME控制器/接口正确安装
- 检查适配器块连接
- 验证ME网络正常工作

#### 3. 权限问题
- 确认服务器令牌正确
- 检查AE2访问权限
- 验证网络访问权限

#### 4. 内存不足
- 升级内存模块
- 优化程序配置
- 减少缓存数据

### 调试模式
在env.lua中启用调试模式：
```lua
env.debug = true  -- 启用详细日志
```

## 性能优化

### 硬件优化
- 使用更高等级的CPU
- 增加内存容量
- 使用SSD硬盘

### 软件优化
- 调整轮询间隔
- 优化缓存设置
- 使用分块传输

### 网络优化
- 使用本地服务器
- 优化网络路由
- 启用压缩传输

## 多客户端部署

### 客户端标识
```lua
-- 为每个客户端设置唯一ID
env.clientId = "client_" .. os.getenv("COMPUTER_ID") or "01"
```

### 负载均衡
- 分配不同的监控任务
- 使用不同的轮询间隔
- 配置不同的AE2连接

## 安全考虑

### 网络安全
- 使用HTTPS连接（如果服务器支持）
- 定期更换服务器令牌
- 限制网络访问权限

### 系统安全
- 定期备份配置文件
- 监控异常活动
- 更新OpenComputers版本

## 维护和更新

### 定期维护
- 重启客户端程序
- 清理日志文件
- 检查系统资源

### 版本更新
1. 备份现有配置
2. 下载新版本文件
3. 更新客户端文件
4. 重启程序

## 联系支持

如果遇到问题，请提供以下信息：
- OpenComputers版本
- 硬件配置
- 错误日志
- 网络环境描述