local capabilities = require "st.capabilities"
local MaxDuration = capabilities["adminmusic34435.maxDuration"]

local ALARM_MAX_DURATION = "maxDuration"

siren_patch = {}

local function maxduration_capability_handler(driver, device, command)
    local maxDuration = command.args.maxDuration
    device:set_field(ALARM_MAX_DURATION, maxDuration)
    device:emit_event(MaxDuration.MaxDuration(maxDuration))
end

siren_patch.maxduration_capability_handler = maxduration_capability_handler

return siren_patch