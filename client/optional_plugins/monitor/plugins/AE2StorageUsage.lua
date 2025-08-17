local component = require("component")
local item = require("item")

-- 获取存放流体存储元件和物品存储元件的ME网络
local fluid_me = component.proxy("9ea46828-732a-4321-8423-193b54450ce2")
local item_me = component.proxy("6a4fb14a-a9e8-498f-a16c-320f377ce7e8")

if not fluid_me or not item_me then
    error("Could not find ME network, please check the network address.")
end

--- 计算AE2流体存储元件的存储使用量和总容量。
--
-- @param fluid_types (number) 存储元件中存储的流体种类数量。
-- @param fluid_count (number) 存储元件中存储的流体总量。
-- @param item_name (string) 存储元件的名称
--
-- @return (number) 存储元件的总使用字节数。
-- @return (number) 存储元件的总容量字节数。
-- @return (number) 存储元件的可存储流体类型数量。
local function calculate_storage_usage(fluid_types, fluid_count, item_name)
    local per_type_bytes = 8 -- 默认每种流体类型占用字节数
    local total_bytes = 0
    local total_types = 1
    if string.find(item_name, "ae2fc:fluid_storage") == 1 then
        per_type_bytes = 8
        local size = string.gsub(item_name, "ae2fc:fluid_storage", "")
        total_bytes = tonumber(size) * 1024
    elseif string.find(item_name, "ae2fc:multi_fluid_storage") == 1 then
        local component_to_per_type = {
            ["1"] = 8,
            ["4"] = 32,
            ["16"] = 128,
            ["64"] = 512,
            ["256"] = 2048,
            ["1024"] = 8192,
            ["4096"] = 32768,
            ["16384"] = 131072,
        }
        local size = string.gsub(item_name, "ae2fc:multi_fluid_storage", "")
        per_type_bytes = component_to_per_type[size] or 8
        total_bytes = tonumber(size) * 1024
        total_types = 5
    end

    local storage_usage = math.ceil(fluid_count / 2048) + (fluid_types * per_type_bytes)

    return math.floor(storage_usage), math.floor(total_bytes), total_types
end


function calculate_fluid_me_totals()
    local total_usage = 0
    local total_capacity = 0
    local used_types = 0
    local total_available_types = 0
    local total_units = 0

    for _, cell in ipairs(fluid_me.getItemsInNetwork()) do
        if not item.hasTag(cell) then
            goto continue
        end
        local data = item.readTag(cell)

        local ft = tonumber(data["ft"]) or 0
        local fc = tonumber(data["fc"]) or 0

        local usage, capacity, types = calculate_storage_usage(ft, fc, cell.name)
        local size = cell.size or 1

        total_usage = total_usage + (usage * size)
        total_capacity = total_capacity + (capacity * size)
        used_types = used_types + (ft * size)
        total_available_types = total_available_types + (types * size)

        total_units = total_units + size

        ::continue::
    end

    return {
        total_usage = total_usage,
        total_capacity = total_capacity,
        used_types = used_types,
        total_available_types = total_available_types,
        total_units = total_units
    }
end


function calculate_item_me_totals()
    local total_usage = 0
    local total_capacity = 0
    local used_types = 0
    local total_available_types = 0
    local total_units = 0

    for _, cell in ipairs(item_me.getItemsInNetwork()) do
        local size = cell.size or 1
        local usedBytes = cell.usedBytes or 0
        local totalBytes = cell.totalBytes or 0
        local storedItemTypes = cell.storedItemTypes or 0
        local getTotalItemTypes = cell.getTotalItemTypes or 0

        total_usage = total_usage + (usedBytes * size)
        total_capacity = total_capacity + (totalBytes * size)
        used_types = used_types + (storedItemTypes * size)
        total_available_types = total_available_types + (getTotalItemTypes * size)

        total_units = total_units + size
    end

    return {
        total_usage = total_usage,
        total_capacity = total_capacity,
        used_types = used_types,
        total_available_types = total_available_types,
        total_units = total_units
    }
end

