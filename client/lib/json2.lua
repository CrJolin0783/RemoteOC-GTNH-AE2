--[[
    Function to serialize Lua tables into JSON format.

    Reference:
    Code adapted from https://github.com/52871299hzy/opencomputer-monitor
]]--

local function dumpjson(  tbl )
    if type(tbl) == 'table' then
        local ret = ''
        local is_array = 0
        local first = 1
        for k,v in pairs(tbl) do
            if first == 1 then
                first = 0
            else
                ret = ret .. ', '
            end
            if type(k) == 'number' then
                is_array = 1
                ret = ret .. dumpjson(v)
            else
                ret = ret .. '"' .. k .. '": ' .. dumpjson(v)
            end
        end
        if is_array == 0 then
            return '{' .. ret .. '}'
        else
            return '[' .. ret .. ']'
        end
    elseif type(tbl) == 'string' then
        tbl = tbl:gsub('&', '%%26')
        return string.format("%q", tbl)
    else
        return tostring(tbl)
    end
end

return dumpjson