local capabilities = require "st.capabilities"
local zcl_commands = require "st.zigbee.zcl.global_commands"
local clusters = require "st.zigbee.zcl.clusters"
local water_patch = require "water_patch"

local CheckInInterval = capabilities["adminmusic34435.checkInInterval"]
local CheckInIntervalCommandName = "setCheckInInterval"
local FastPollTimeout = capabilities["adminmusic34435.fastPollTimeout"]
local FastPollTimeoutCommandName = "setFastPollTimeout"
local IdentifyTime = capabilities["adminmusic34435.identifyTime"]
local IdentifyTimeCommandName = "setIdentifyTime"
local DeviceEnabled = capabilities["adminmusic34435.deviceEnabled"]
local DeviceEnabledCommandName = "setDeviceEnabled"

-- add more models if they also have these attributes
local PATCHED_DEVICE_MODELS = {
    { mfr = "Third Reality, Inc", model = "3RWS18BZ" }
}
  
local check_patched_device_models = function(opts, driver, device)
    for _, fingerprint in ipairs(PATCHED_DEVICE_MODELS) do
        if device:get_model() == fingerprint.model then
            return true
        end
    end
    return false
end

local CLUSTER_ATTR_PAIRS = {
    {clusters.PollControl.ID, { clusters.PollControl.attributes.CheckInInterval.ID, clusters.PollControl.attributes.FastPollTimeout.ID } },
    {clusters.Basic.ID, { clusters.Basic.attributes.DeviceEnabled.ID } },
    {clusters.Identify.ID, { clusters.Identify.attributes.IdentifyTime.ID } },
}
    
local function device_init(driver, device)
    for i = 1, #CLUSTER_ATTR_PAIRS do
        cluster_id = CLUSTER_ATTR_PAIRS[i][1]
        attribute_ids = CLUSTER_ATTR_PAIRS[i][2]
        water_patch.init_capability_values(device, cluster_id, attribute_ids, nil)
    end
end

local water_patch_handler = {
  NAME = "Water Patched Handler",
  lifecycle_handlers = {
    init = device_init,
  },
  capability_handlers = {
    [CheckInInterval.ID] = { [CheckInIntervalCommandName] = water_patch.checkininterval_capability_handler },
    [FastPollTimeout.ID] = { [FastPollTimeoutCommandName] = water_patch.fastpolltimeout_capability_handler },
    [IdentifyTime.ID] = { [IdentifyTimeCommandName] = water_patch.identifytime_capability_handler },
    [DeviceEnabled.ID] = { [DeviceEnabledCommandName] = water_patch.deviceenabled_capability_handler }
  },
  zigbee_handlers = {
    global = {
      [clusters.PollControl.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = water_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = water_patch.read_attr_res_handler
      },
      [clusters.Identify.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = water_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = water_patch.read_attr_res_handler
      },
      [clusters.Basic.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = water_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = water_patch.read_attr_res_handler
      }
    }
  },
  can_handle = check_patched_device_models
}

return water_patch_handler