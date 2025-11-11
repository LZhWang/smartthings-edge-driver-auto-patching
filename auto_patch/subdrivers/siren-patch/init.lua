local capabilities = require "st.capabilities"
local MaxDuration = capabilities["adminmusic34435.maxDuration"]
local MaxDurationCommandName = "setMaxDuration"
local siren_patch = require "siren_patch"

local ALARM_DEFAULT_MAX_DURATION = 0x00B4


local PATCHED_DEVICE_MODELS = {
    { mfr = "frient A/S", model = "SIRZB-110" }
}

local check_patched_device_models = function(opts, driver, device)
    for _, fingerprint in ipairs(PATCHED_DEVICE_MODELS) do
        if device:get_model() == fingerprint.model then
            return true
        end
    end
        return false
end

-- initialize maxduration in App UI
local function device_init(driver, device)
  device:emit_event(MaxDuration.MaxDuration(ALARM_DEFAULT_MAX_DURATION))
end

local frient_patched_driver = {
  NAME = "frient siren patched handler",
  lifecycle_handlers = {
    init = device_init,
  },
  capability_handlers = {
    [MaxDuration.ID] = {
      [MaxDurationCommandName] = siren_patch.maxduration_capability_handler
    }
  },
  can_handle = check_patched_device_models
}

return frient_patched_driver