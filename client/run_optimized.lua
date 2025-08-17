local event = require("event")
local computer = require("computer")
local os = require("os")

-- 根据配置选择执行器
local env = require("env")
local logger = require("lib/logger")

local executor
local useOptimized = false  -- 可以通过环境变量或配置文件控制

local args = {...}
if #args >= 1 then
    if args[1] == "--debug" then
        logger.set_level("DEBUG")
        logger.debug("Debug mode has been enabled.")
    elseif args[1] == "--optimized" then
        useOptimized = true
        logger.info("Using optimized executor")
    end
end

-- 初始化执行器
if useOptimized then
    local success, OptimizedExecutor = pcall(require, "src.optimized_executor")
    if success then
        executor = OptimizedExecutor
        logger.info("Optimized executor loaded successfully")
    else
        logger.warn("Failed to load optimized executor, falling back to standard executor")
        executor = require("src.executor")
    end
else
    executor = require("src.executor")
    logger.info("Standard executor loaded")
end

local timerId
local shouldExit = false
local statsTimerId

-- 性能监控
local performanceStats = {
    startTime = computer.uptime(),
    lastStatsTime = computer.uptime(),
    totalPolls = 0,
    successfulPolls = 0,
    failedPolls = 0,
    memoryUsage = {}
}

local function logPerformanceStats()
    local currentTime = computer.uptime()
    local uptime = currentTime - performanceStats.startTime
    local freeMemory = computer.freeMemory()
    
    performanceStats.memoryUsage[#performanceStats.memoryUsage + 1] = {
        time = currentTime,
        memory = freeMemory
    }
    
    -- 保持最近100条内存记录
    if #performanceStats.memoryUsage > 100 then
        table.remove(performanceStats.memoryUsage, 1)
    end
    
    local avgPollTime = uptime / math.max(performanceStats.totalPolls, 1)
    local successRate = performanceStats.successfulPolls / math.max(performanceStats.totalPolls, 1) * 100
    
    logger.info(string.format("Performance Stats - Uptime: %.1fs, Polls: %d, Success: %.1f%%, Avg Poll Time: %.2fs, Free Memory: %.1fKB",
        uptime, performanceStats.totalPolls, successRate, avgPollTime, freeMemory / 1024))
    
    performanceStats.lastStatsTime = currentTime
end

local function pollServer()
    local success, info = xpcall(function()
        if shouldExit then
            logger.info("Exiting polling...")
            if timerId then event.cancel(timerId) end
            if statsTimerId then event.cancel(statsTimerId) end
            return
        end
        
        performanceStats.totalPolls = performanceStats.totalPolls + 1
        
        logger.debug(string.format("Polling... Free Memory: %.1fKB", computer.freeMemory() / 1024))
        
        local taskId, command_table, isChunked
        
        if useOptimized and executor.fetchCommands then
            -- 使用优化执行器
            taskId, command_table, isChunked = executor:fetchCommands()
        else
            -- 使用标准执行器
            taskId, command_table, isChunked = executor.fetchCommands()
        end
        
        os.sleep(0.1)  -- 短暂休眠避免CPU占用过高
        
        if taskId and command_table then
            logger.info("Processing task: " .. tostring(taskId))
            
            local command_result_table
            if useOptimized and executor.executeCommands then
                command_result_table = executor:executeCommands(command_table, isChunked)
            else
                command_result_table = executor.processCommands(command_table, isChunked)
            end
            
            os.sleep(0.1)
            
            logger.debug("Reporting results for Task ID: " .. tostring(taskId))
            
            local reportSuccess
            if isChunked then
                if useOptimized and executor.reportResults then
                    reportSuccess = executor:reportResults(taskId, command_result_table, true)
                else
                    reportSuccess = executor.reportChunkedResults(taskId, command_result_table[1])
                end
            else
                if useOptimized and executor.reportResults then
                    reportSuccess = executor:reportResults(taskId, command_result_table, false)
                else
                    reportSuccess = executor.reportResults(taskId, command_result_table)
                end
            end
            
            if reportSuccess then
                performanceStats.successfulPolls = performanceStats.successfulPolls + 1
                logger.info("Task completed successfully: " .. tostring(taskId))
            else
                logger.error("Failed to report results for task: " .. tostring(taskId))
            end
        else
            logger.debug("No commands received or invalid response.")
        end
        
        -- 内存清理
        if computer.freeMemory() < 1024 * 1024 then  -- 小于1MB时强制垃圾回收
            logger.debug("Low memory detected, forcing garbage collection")
            collectgarbage("collect")
        end
        
    end, debug.traceback)
    
    if not success then
        logger.error("Polling error: " .. tostring(info))
        performanceStats.failedPolls = performanceStats.failedPolls + 1
        
        -- 错误处理：连续失败多次时增加轮询间隔
        if performanceStats.failedPolls > 5 then
            logger.warn("Multiple consecutive failures, increasing polling interval")
            env.pollingInterval = math.min(env.pollingInterval * 1.5, 60)  -- 最大60秒
        end
    else
        -- 成功后恢复默认轮询间隔
        if env.pollingInterval > 8 then
            env.pollingInterval = 8
            logger.debug("Restored default polling interval")
        end
    end
end

-- 键盘事件处理
local function handleKeyboardEvents()
    while true do
        local eventType, _, char, code = event.pull("key_down")
        
        if eventType == "key_down" then
            if code == 16 then  -- Q键
                logger.info("Q key pressed, shutting down...")
                shouldExit = true
                break
            elseif code == 18 then  -- S键
                logPerformanceStats()
            elseif code == 19 then  -- D键
                logger.set_level(logger.get_level() == "DEBUG" and "INFO" or "DEBUG")
                logger.info("Toggled debug mode: " .. (logger.get_level() == "DEBUG" and "ON" or "OFF"))
            end
        end
    end
end

-- 启动性能统计定时器
statsTimerId = event.timer(60, logPerformanceStats, math.huge)  -- 每分钟记录一次统计

-- 启动主轮询定时器
timerId = event.timer(env.pollingInterval, pollServer, math.huge)

-- 启动键盘事件监听
event.fork(handleKeyboardEvents)

logger.info("=== RemoteOC Client Started ===")
logger.info(string.format("Start time: %s", os.date("%Y-%m-%d %H:%M:%S")))
logger.info(string.format("Client ID: %s", env.clientId))
logger.info(string.format("Server: %s", env.baseUrl))
logger.info(string.format("Polling interval: %ds", env.pollingInterval))
logger.info(string.format("Executor: %s", useOptimized and "Optimized" or "Standard"))
logger.info("Press Q to quit, S for stats, D for debug toggle")

-- 主循环
while true do
    local eventType = event.pull()
    if eventType == "interrupted" then
        shouldExit = true
        if timerId and event.cancel(timerId) then
            logger.info("Interrupt received, shutting down...")
        end
        if statsTimerId and event.cancel(statsTimerId) then
            logger.info("Performance stats timer cancelled")
        end
        break
    end
end

-- 最终统计
logPerformanceStats()
logger.info("=== RemoteOC Client Stopped ===")