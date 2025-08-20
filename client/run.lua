local event = require("event")
local computer = require("computer")
local os = require("os")

local executor = require("src.executor")
local env = require("env")
local logger = require("lib/logger")

local timerId  -- 存储轮询计时器的 ID
local autoUploadTimerId  -- 存储自动上传计时器的 ID
local shouldExit = false  -- 退出标志

-- 记录上次上传时间
local lastCpuUploadTime = 0
local lastItemUploadTime = 0

local args = {...}
if #args >= 1 then
    if args[1] == "--debug" then
        logger.set_level("DEBUG")
        logger.debug("Debug mode has been enabled.")
    end
end

local function pollServer()
    local success, info = xpcall(function()
        -- 检查是否需要退出
        if shouldExit then
            logger.info("Exiting polling...")
            event.cancel(timerId)  -- 取消定时器
            return
        end

        logger.debug("Polling... Free Memory: ".. require("computer").freeMemory())

        -- 获取命令和 taskId
        local taskId, command_table, isChunked = executor.fetchCommands()
        os.sleep(0)

        if isChunked then
            logger.debug("Using chunked upload")
        end

        if taskId and command_table then
            -- 处理命令并获取结果
            local command_result_table = executor.processCommands(command_table, isChunked)
            os.sleep(0)

            logger.debug("Reporting results for Task ID: " .. tostring(taskId))
            -- 将执行结果和 taskId 一起报告回服务器
            if isChunked then
                executor.reportChunkedResults(taskId, command_result_table[1])
            else
                executor.reportResults(taskId, command_result_table)
            end
        else
            logger.debug("No commands received or invalid response.")
        end
    end, debug.traceback)

    -- 处理发生的任何错误
    if not success then
        logger.error(info)
    end
end

local function autoUploadData()
    local success, info = xpcall(function()
        local currentTime = computer.uptime()
        
        -- 检查是否需要上传CPU数据
        local cpuInterval = env.autoUploadCpuInterval or 30
        if currentTime - lastCpuUploadTime >= cpuInterval then
            logger.debug("Auto uploading CPU data...")
            
            -- 获取CPU数据
            local cpuData = ae.getCpuList(true)
            if cpuData and cpuData.message == "success" then
                -- 上传CPU数据到服务端缓存
                local uploadResult = executor.uploadDataToCache("cpu", cpuData)
                if uploadResult then
                    logger.info("CPU data uploaded successfully")
                    lastCpuUploadTime = currentTime
                else
                    logger.error("Failed to upload CPU data")
                end
            else
                logger.error("Failed to get CPU data: " .. tostring(cpuData and cpuData.message or "Unknown error"))
            end
        end
        
        -- 检查是否需要上传物品数据
        local itemInterval = env.autoUploadItemInterval or 60
        if currentTime - lastItemUploadTime >= itemInterval then
            logger.debug("Auto uploading item data...")
            
            -- 获取物品数据
            local itemData = ae.getAllSilempleItems()
            if itemData and itemData.message == "success" then
                -- 上传物品数据到服务端缓存
                local uploadResult = executor.uploadDataToCache("item", itemData)
                if uploadResult then
                    logger.info("Item data uploaded successfully")
                    lastItemUploadTime = currentTime
                else
                    logger.error("Failed to upload item data")
                end
            else
                logger.error("Failed to get item data: " .. tostring(itemData and itemData.message or "Unknown error"))
            end
        end
    end, debug.traceback)
    
    if not success then
        logger.error("Error in autoUploadData: " .. tostring(info))
    end
end

-- 启动定时器
timerId = event.timer(env.pollingInterval or 8, pollServer, math.huge)

-- 检查自动上传配置并启动定时器
local uploadInterval = env.autoUploadInterval or 30
if uploadInterval > 0 then
    autoUploadTimerId = event.timer(uploadInterval, autoUploadData, math.huge)
    logger.info("Auto upload timer started with interval: " .. uploadInterval .. "s")
else
    logger.info("Auto upload disabled")
end

logger.info("Program started at " .. os.date("%Y-%m-%d %H:%M:%S"))
logger.info("Polling interval: " .. (env.pollingInterval or 8) .. "s, Auto upload interval: " .. (env.autoUploadInterval or 30) .. "s")

while true do
    local eventType = event.pull()
    if eventType == "interrupted" then
        shouldExit = true
        local cancelled1 = event.cancel(timerId)
        local cancelled2 = true
        -- 只有当自动上传定时器存在时才取消它
        if autoUploadTimerId then
            cancelled2 = event.cancel(autoUploadTimerId)
        end
        if cancelled1 and cancelled2 then
            logger.info("Interrupt received, shutting down...")
        else
            logger.error("Error cancelling timers")
        end
        break
    end
end
