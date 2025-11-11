local capabilities = require "st.capabilities"
local zcl_commands = require "st.zigbee.zcl.global_commands"
local clusters = require "st.zigbee.zcl.clusters"
local hue_patch = require "hue_patch"

local PIROccupiedToUnoccupiedDelay = capabilities["adminmusic34435.pirOccupiedToUnoccupiedDelay"]
local PIROccupiedToUnoccupiedDelayCommandName = "setPIROccupiedToUnoccupiedDelay"
local HueMotionSensitivity = capabilities["adminmusic34435.hueMotionSensitivity"]
local HueMotionSensitivityCommandName = "setHueMotionSensitivity"

-- add more models if they also have these attributes
local PATCHED_DEVICE_MODELS = {
    { mfr = "Philips", model = "SML001" }
}
  
local check_patched_device_models = function(opts, driver, device)
    for _, fingerprint in ipairs(PATCHED_DEVICE_MODELS) do
        if device:get_model() == fingerprint.model then
            return true
        end
    end
    return false
end


CLUSTER_ID = clusters.OccupancySensing.ID
ATTR_IDS = {
  clusters.OccupancySensing.attributes.PIROccupiedToUnoccupiedDelay.ID,
}

local function device_init(driver, device)
    hue_patch.init_capability_values(device, CLUSTER_ID, ATTR_IDS, nil)
    hue_patch.init_capability_values(device, CLUSTER_ID, { 0x0030 }, 0x100B)
end

local hue_patch_handler = {
  NAME = "Hue Motion Patched Handler",
  lifecycle_handlers = {
    init = device_init,
  },
  capability_handlers = {
    [PIROccupiedToUnoccupiedDelay.ID] = { [PIROccupiedToUnoccupiedDelayCommandName] = hue_patch.piroccupiedtounoccupieddelay_capability_handler },
    [HueMotionSensitivity.ID] = { [HueMotionSensitivityCommandName] = hue_patch.huemotionsensitivity_capability_handler } 
  },
  zigbee_handlers = {
    global = {
      [clusters.OccupancySensing.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = hue_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = hue_patch.read_attr_res_handler
      }
    }
  },
  can_handle = check_patched_device_models
}

return hue_patch_handler