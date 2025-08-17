-- 客户端数据去重模块
-- 用于避免重复处理相同的数据请求

local json = require("lib/json")
local logger = require("lib/logger")

local deduplicator = {
    -- 数据缓存表
    dataCache = {},
    -- 请求历史记录
    requestHistory = {},
    -- 指纹缓存
    fingerprintCache = {},
    -- 缓存配置
    config = {
        maxCacheSize = 1000,        -- 最大缓存条目数
        cacheTTL = 300,            -- 缓存生存时间（秒）
        maxHistorySize = 100,      -- 最大历史记录数
        enableFingerprintCheck = true  -- 启用指纹检查
    }
}

-- 生成数据指纹
local function generateFingerprint(data)
    if type(data) ~= "table" then
        return tostring(data)
    end
    
    -- 简单的指纹生成算法
    local fingerprint = ""
    local keys = {}
    for k, v in pairs(data) do
        table.insert(keys, k)
    end
    table.sort(keys)
    
    for _, key in ipairs(keys) do
        local value = data[key]
        if type(value) == "table" then
            fingerprint = fingerprint .. key .. ":" .. generateFingerprint(value) .. "|"
        else
            fingerprint = fingerprint .. key .. ":" .. tostring(value) .. "|"
        end
    end
    
    -- 使用简单的哈希函数
    local hash = 0
    for i = 1, #fingerprint do
        hash = ((hash * 31) + fingerprint:byte(i)) % 2147483647
    end
    
    return tostring(hash)
end

-- 清理过期的缓存
local function cleanupCache()
    local currentTime = os.time()
    local cleanedCount = 0
    
    -- 清理数据缓存
    for key, entry in pairs(deduplicator.dataCache) do
        if currentTime - entry.timestamp > deduplicator.config.cacheTTL then
            deduplicator.dataCache[key] = nil
            cleanedCount = cleanedCount + 1
        end
    end
    
    -- 清理指纹缓存
    for key, entry in pairs(deduplicator.fingerprintCache) do
        if currentTime - entry.timestamp > deduplicator.config.cacheTTL then
            deduplicator.fingerprintCache[key] = nil
            cleanedCount = cleanedCount + 1
        end
    end
    
    -- 如果缓存太大，清理最旧的条目
    local dataCacheSize = 0
    for _ in pairs(deduplicator.dataCache) do
        dataCacheSize = dataCacheSize + 1
    end
    
    if dataCacheSize > deduplicator.config.maxCacheSize then
        local toRemove = dataCacheSize - deduplicator.config.maxCacheSize
        local oldestKeys = {}
        
        for key, entry in pairs(deduplicator.dataCache) do
            table.insert(oldestKeys, {key = key, timestamp = entry.timestamp})
        end
        
        table.sort(oldestKeys, function(a, b) return a.timestamp < b.timestamp end)
        
        for i = 1, toRemove do
            if oldestKeys[i] then
                deduplicator.dataCache[oldestKeys[i].key] = nil
            end
        end
    end
    
    if cleanedCount > 0 then
        logger.debug("Cleaned up " .. cleanedCount .. " expired cache entries")
    end
end

-- 检查是否为重复请求
function deduplicator.isDuplicateRequest(requestType, params)
    cleanupCache()
    
    -- 生成请求指纹
    local requestFingerprint = requestType .. ":" .. generateFingerprint(params)
    local currentTime = os.time()
    
    -- 检查指纹缓存
    if deduplicator.config.enableFingerprintCheck then
        local cached = deduplicator.fingerprintCache[requestFingerprint]
        if cached and (currentTime - cached.timestamp < deduplicator.config.cacheTTL) then
            logger.debug("Duplicate request detected: " .. requestFingerprint)
            return true, cached.data
        end
    end
    
    -- 检查请求历史
    for _, history in ipairs(deduplicator.requestHistory) do
        if history.fingerprint == requestFingerprint and 
           (currentTime - history.timestamp < deduplicator.config.cacheTTL) then
            logger.debug("Duplicate request found in history: " .. requestFingerprint)
            return true, history.data
        end
    end
    
    return false, nil
end

-- 缓存请求结果
function deduplicator.cacheRequest(requestType, params, data)
    local requestFingerprint = requestType .. ":" .. generateFingerprint(params)
    local currentTime = os.time()
    
    -- 缓存到指纹缓存
    deduplicator.fingerprintCache[requestFingerprint] = {
        data = data,
        timestamp = currentTime
    }
    
    -- 添加到请求历史
    table.insert(deduplicator.requestHistory, {
        fingerprint = requestFingerprint,
        data = data,
        timestamp = currentTime
    })
    
    -- 限制历史记录大小
    if #deduplicator.requestHistory > deduplicator.config.maxHistorySize then
        table.remove(deduplicator.requestHistory, 1)
    end
    
    logger.debug("Cached request result: " .. requestFingerprint)
end

-- 缓存数据
function deduplicator.cacheData(key, data)
    cleanupCache()
    
    deduplicator.dataCache[key] = {
        data = data,
        timestamp = os.time()
    }
    
    logger.debug("Cached data with key: " .. key)
end

-- 获取缓存的数据
function deduplicator.getCachedData(key)
    cleanupCache()
    
    local cached = deduplicator.dataCache[key]
    if cached and (os.time() - cached.timestamp < deduplicator.config.cacheTTL) then
        logger.debug("Retrieved cached data for key: " .. key)
        return cached.data
    end
    
    return nil
end

-- 检查数据是否已存在（基于内容）
function deduplicator.isDataExists(data)
    if type(data) ~= "table" then
        return false
    end
    
    local fingerprint = generateFingerprint(data)
    return deduplicator.fingerprintCache[fingerprint] ~= nil
end

-- 获取缓存统计信息
function deduplicator.getCacheStats()
    local dataCacheSize = 0
    local fingerprintCacheSize = 0
    local historySize = #deduplicator.requestHistory
    
    for _ in pairs(deduplicator.dataCache) do
        dataCacheSize = dataCacheSize + 1
    end
    
    for _ in pairs(deduplicator.fingerprintCache) do
        fingerprintCacheSize = fingerprintCacheSize + 1
    end
    
    return {
        dataCacheSize = dataCacheSize,
        fingerprintCacheSize = fingerprintCacheSize,
        historySize = historySize,
        maxCacheSize = deduplicator.config.maxCacheSize,
        cacheTTL = deduplicator.config.cacheTTL
    }
end

-- 清空所有缓存
function deduplicator.clearCache()
    deduplicator.dataCache = {}
    deduplicator.fingerprintCache = {}
    deduplicator.requestHistory = {}
    logger.info("All caches cleared")
end

-- 更新配置
function deduplicator.updateConfig(newConfig)
    for key, value in pairs(newConfig) do
        if deduplicator.config[key] ~= nil then
            deduplicator.config[key] = value
            logger.debug("Updated deduplicator config: " .. key .. " = " .. tostring(value))
        end
    end
end

-- 初始化去重器
function deduplicator.initialize(config)
    if config then
        deduplicator.updateConfig(config)
    end
    logger.info("Data deduplicator initialized with config: " .. json.encode(deduplicator.config))
end

return deduplicator