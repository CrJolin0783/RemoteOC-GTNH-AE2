local component = require("component")

-- get the capacitor bank
local capacitor = component.proxy("91d6e3f9-81cf-4f66-b51f-4eb2a9bf28b8")

if capacitor == nil then
    error("Cannot find capacitor bank, please check the network address.")
end

function getCapacitorInfo()
    return capacitor.getSensorInformation();
end
