-- 优化的OpenComputers客户端实现
local internet = require("internet")
local computer = require("computer")
local os = require("os")
local filesystem = require("filesystem")
local shell = require("shell")

local env = require("env")
local logger = require("lib/logger")
local json = require("lib/json")
local dumpjson = require("lib/json2")

local OptimizedExecutor = {
    baseUrl = env.baseUrl,
    clientId = env.clientId,
    serverToken = env.serverToken,
    chunkSize = env.chunkSize or 256,
    pollingInterval = env.pollingInterval or 8,
    
    -- 新增配置
    useWebSocket = false,  -- 是否使用WebSocket（需要服务器支持）
    useCompression = true,  -- 启用数据压缩
    incrementalSync = true,  -- 启用增量同步
    maxRetries = 3,  -- 最大重试次数
    requestTimeout = 5,  -- 请求超时时间（秒）
    
    -- 内部状态
    wsConnection = nil,
    lastKnownFingerprints = {},
    syncStats = {
        totalRequests = 0,
        successfulRequests = 0,
        failedRequests = 0,
        bytesSent = 0,
        bytesReceived = 0,
        lastSyncTime = 0
    }
}

function OptimizedExecutor:init()
    logger.info("Initializing optimized executor...")
    
    -- 尝试建立WebSocket连接
    if self.useWebSocket then
        self:_connectWebSocket()
    end
    
    logger.info("Optimized executor initialized successfully")
end

function OptimizedExecutor:_connectWebSocket()
    -- WebSocket连接逻辑（需要OpenComputers WebSocket支持）
    -- 由于OpenComputers的限制，这里暂时保留接口
    logger.info("WebSocket connection not supported in this version")
    self.useWebSocket = false
end

function OptimizedExecutor:_getHeaders()
    return {
        ["Content-Type"] = "application/json",
        ["X-Client-ID"] = self.clientId,
        ["X-Server-Token"] = self.serverToken,
        ["X-Optimized"] = "true",
        ["X-Incremental"] = tostring(self.incrementalSync)
    }
end

function OptimizedExecutor:_makeRequest(url, data, method)
    method = method or "GET"
    local retries = 0
    
    while retries < self.maxRetries do
        try
            local startTime = computer.uptime()
            local headers = self:_getHeaders()
            
            local req
            if method == "POST" then
                req = internet.request(url, data, headers)
            else
                req = internet.request(url, nil, headers)
            end
            
            -- 等待连接建立
            local connectStart = computer.uptime()
            while not req.finishConnect() do
                if computer.uptime() - connectStart > self.requestTimeout then
                    error("Request timeout")
                end
                os.sleep(0.1)
            end
            
            -- 读取响应
            local response = ""
            local chunk
            repeat
                chunk = req.read()
                if chunk then
                    response = response .. chunk
                end
            until not chunk
            
            -- 更新统计信息
            local requestTime = computer.uptime() - startTime
            self.syncStats.bytesReceived = self.syncStats.bytesReceived + #response
            self.syncStats.lastSyncTime = computer.uptime()
            
            req.close()
            
            return response
            
        catch err
            retries = retries + 1
            logger.warn(string.format("Request failed (attempt %d/%d): %s", retries, self.maxRetries, tostring(err)))
            
            if retries < self.maxRetries then
                os.sleep(1)  -- 等待1秒后重试
            else
                self.syncStats.failedRequests = self.syncStats.failedRequests + 1
                error(err)
            end
        end
    end
end

function OptimizedExecutor:fetchCommands()
    self.syncStats.totalRequests = self.syncStats.totalRequests + 1
    
    local url = self.baseUrl .. env.getPath .. 
                "?incremental=" .. tostring(self.incrementalSync) ..
                "&optimized=true"
    
    try
        local response = self:_makeRequest(url)
        
        if response == "" then
            return nil, nil, nil
        end
        
        local res = json.decode(response)
        
        if not res or res.code ~= 200 then
            logger.warn("Failed to fetch commands: " .. (res.message or "unknown error"))
            return nil, nil, nil
        end
        
        local data = res.data
        if not data or not data.taskId or not data.commands then
            return nil, nil, nil
        end
        
        -- 检查是否为增量同步（无变化）
        if data.sync_type == "no_change" then
            logger.info("No data changes detected, skipping processing")
            return data.taskId, {}, false
        end
        
        self.syncStats.successfulRequests = self.syncStats.successfulRequests + 1
        logger.debug("Fetched commands for task: " .. data.taskId)
        
        return data.taskId, data.commands, data.is_chunked or false
        
    catch err
        logger.error("Error fetching commands: " .. tostring(err))
        return nil, nil, nil
    end
end

function OptimizedExecutor:executeCommands(commands, isChunked)
    logger.debug("Executing " .. #commands .. " commands...")
    
    local results = {}
    local startTime = computer.uptime()
    
    -- 加载插件
    self:_loadPlugins()
    
    for i, command in ipairs(commands) do
        try
            local success, result = self:_executeCommand(command)
            
            if success then
                if isChunked and result.message == "success" then
                    results[i] = result.data
                else
                    results[i] = json.encode(result)
                end
            else
                results[i] = json.encode({message = tostring(result)})
            end
            
            -- 每50个命令后挂起一次，避免超时
            if i % 50 == 0 then
                os.sleep(0)
            end
            
        catch err
            logger.error("Error executing command " .. i .. ": " .. tostring(err))
            results[i] = json.encode({message = "Command execution failed: " .. tostring(err)})
        end
    end
    
    local executionTime = computer.uptime() - startTime
    logger.debug(string.format("Commands executed in %.2f seconds", executionTime))
    
    return results
end

function OptimizedExecutor:_executeCommand(command)
    logger.debug("Executing command: " .. tostring(command))
    
    local code, loadError = load(command)
    if not code then
        return false, "Failed to load command: " .. tostring(loadError)
    end
    
    local success, result = xpcall(code, debug.traceback)
    
    if not success then
        return false, tostring(result)
    end
    
    return true, result
end

function OptimizedExecutor:reportResults(taskId, results, isChunked)
    logger.debug("Reporting results for task: " .. taskId)
    
    if isChunked then
        return self:_reportChunkedResults(taskId, results)
    else
        return self:_reportResults(taskId, results)
    end
end

function OptimizedExecutor:_reportResults(taskId, results)
    local reportData = {
        task_id = taskId,
        results = results
    }
    
    local jsonData = dumpjson(reportData)
    self.syncStats.bytesSent = self.syncStats.bytesSent + #jsonData
    
    try
        local response = self:_makeRequest(
            self.baseUrl .. env.reportPath,
            jsonData,
            "POST"
        )
        
        logger.debug("Results reported successfully")
        return true
        
    catch err
        logger.error("Error reporting results: " .. tostring(err))
        return false
    end
end

function OptimizedExecutor:_reportChunkedResults(taskId, results)
    local chunkSize = self.chunkSize
    local totalResults = #results
    
    for i = 1, totalResults, chunkSize do
        local chunkEnd = math.min(i + chunkSize - 1, totalResults)
        local chunkResults = {}
        
        for j = i, chunkEnd do
            table.insert(chunkResults, results[j])
        end
        
        local chunked = i
        if chunkEnd >= totalResults then
            chunked = 0
        end
        
        local reportData = {
            task_id = taskId,
            results = chunkResults
        }
        
        local jsonData = json.encode(reportData)
        local url = self.baseUrl .. env.chunkedReportPath .. "?chunked=" .. tostring(chunked)
        
        try
            local response = self:_makeRequest(url, jsonData, "POST")
            logger.debug(string.format("Chunk %d reported successfully", chunked))
            
        catch err
            logger.error(string.format("Error reporting chunk %d: %s", chunked, tostring(err)))
            return false
        end
        
        -- 如果不是最后一块，等待一下
        if chunked ~= 0 then
            os.sleep(0.2)
        end
    end
    
    logger.debug("All chunked results reported successfully")
    return true
end

function OptimizedExecutor:_loadPlugins()
    package.path = package.path .. ";" .. shell.resolve("lib/") .. "/?.lua"
    local pluginPath = shell.resolve("plugins/")
    
    for file in filesystem.list(pluginPath) do
        if file:match("%.lua$") then
            local moduleName = file:sub(1, -5)
            try
                require("plugins/" .. moduleName)
                logger.info("Loaded plugin: " .. moduleName)
            catch err
                logger.error("Error loading plugin " .. moduleName .. ": " .. tostring(err))
            end
        end
    end
end

function OptimizedExecutor:getStats()
    return {
        syncStats = self.syncStats,
        config = {
            useWebSocket = self.useWebSocket,
            useCompression = self.useCompression,
            incrementalSync = self.incrementalSync,
            pollingInterval = self.pollingInterval,
            chunkSize = self.chunkSize
        }
    }
end

function OptimizedExecutor:run()
    logger.info("Starting optimized executor...")
    self:init()
    
    while true do
        try
            local taskId, commands, isChunked = self:fetchCommands()
            
            if taskId and commands and #commands > 0 then
                logger.info("Processing task: " .. taskId)
                
                local results = self:executeCommands(commands, isChunked)
                
                if results and #results > 0 then
                    local success = self:reportResults(taskId, results, isChunked)
                    
                    if success then
                        logger.info("Task completed successfully: " .. taskId)
                    else
                        logger.error("Failed to report results for task: " .. taskId)
                    end
                else
                    logger.warn("No results generated for task: " .. taskId)
                end
            else
                logger.debug("No commands to execute")
            end
            
        catch err
            logger.error("Error in main loop: " .. tostring(err))
        end
        
        os.sleep(self.pollingInterval)
    end
end

-- 返回优化后的执行器
return OptimizedExecutor