local capabilities = require "st.capabilities"
local zcl_commands = require "st.zigbee.zcl.global_commands"
local clusters = require "st.zigbee.zcl.clusters"
local switch_patch = require "switch_patch"

local IdentifyTime = capabilities["adminmusic34435.identifyTime"]
local IdentifyTimeCommandName = "setIdentifyTime"
local DeviceEnabled = capabilities["adminmusic34435.deviceEnabled"]
local DeviceEnabledCommandName = "setDeviceEnabled"
local OnOffTransitionTime = capabilities["adminmusic34435.onOffTransitionTime"]
local OnOffTransitionTimeCommandName = "setOnOffTransitionTime"
local OnLevel = capabilities["adminmusic34435.onLevel"]
local OnLevelCommandName = "setOnLevel"
local OnTime = capabilities["adminmusic34435.onTime"]
local OnTimeCommandName = "setOnTime"
local OffWaitTime = capabilities["adminmusic34435.offWaitTime"]
local OffWaitTimeCommandName = "setOffWaitTime"
local StartUpOnOff = capabilities["adminmusic34435.startUpOnOff"]
local StartUpOnOffCommandName = "setStartUpOnOff"
local StartUpColorTemperatureMireds = capabilities["adminmusic34435.startUpColorTemperatureMireds"]
local StartUpColorTemperatureMiredsCommandName = "setStartUpColorTemperatureMireds"

-- add more models if they also have these attributes
local PATCHED_DEVICE_MODELS = {
    { mfr = "innr", model = "SP 224" },
    { mfr = "innr", model = "AE 280 C" },
    { mfr = "sengled", model = "E21-N1EA" },
    { mfr = "SONOFF", model = "S31 Lite zb" }
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
  {clusters.Basic.ID, { clusters.Basic.attributes.DeviceEnabled.ID } },
  {clusters.Identify.ID, { clusters.Identify.attributes.IdentifyTime.ID } },
  {clusters.Level.ID, { clusters.Level.attributes.OnOffTransitionTime.ID, clusters.Level.attributes.OnLevel.ID } },
  {clusters.OnOff.ID, { clusters.OnOff.attributes.OnTime.ID, clusters.OnOff.attributes.OffWaitTime.ID, clusters.OnOff.attributes.StartUpOnOff.ID } },
  {clusters.ColorControl.ID, { clusters.ColorControl.attributes.StartUpColorTemperatureMireds.ID } }
}


local function device_init(driver, device)
  for i = 1, #CLUSTER_ATTR_PAIRS do
    cluster_id = CLUSTER_ATTR_PAIRS[i][1]
    attribute_ids = CLUSTER_ATTR_PAIRS[i][2]
    switch_patch.init_capability_values(device, cluster_id, attribute_ids, nil)
  end
end

local switch_patch_handler = {
  NAME = "Switch Patched Handler",
  lifecycle_handlers = {
    init = device_init,
  },
  capability_handlers = {
    [IdentifyTime.ID] = { [IdentifyTimeCommandName] = switch_patch.identifytime_capability_handler },
    [DeviceEnabled.ID] = { [DeviceEnabledCommandName] = switch_patch.deviceenabled_capability_handler },
    [OnOffTransitionTime.ID] = { [OnOffTransitionTimeCommandName] = switch_patch.onofftransitiontime_capability_handler },
    [OnLevel.ID] = { [OnLevelCommandName] = switch_patch.onlevel_capability_handler },
    [OnTime.ID] = { [OnTimeCommandName] = switch_patch.ontime_capability_handler },
    [OffWaitTime.ID] = { [OffWaitTimeCommandName] = switch_patch.offwaittime_capability_handler },
    [StartUpOnOff.ID] = { [StartUpOnOffCommandName] = switch_patch.startuponoff_capability_handler },
    [StartUpColorTemperatureMireds.ID] = { [StartUpColorTemperatureMiredsCommandName] = switch_patch.startupcolortemperaturemireds_capability_handler }
  },
  zigbee_handlers = {
    global = {
      [clusters.Identify.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = switch_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = switch_patch.read_attr_res_handler
      },
      [clusters.Basic.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = switch_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = switch_patch.read_attr_res_handler
      },
      [clusters.Level.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = switch_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = switch_patch.read_attr_res_handler
      },
      [clusters.OnOff.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = switch_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = switch_patch.read_attr_res_handler
      },
      [clusters.ColorControl.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = switch_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = switch_patch.read_attr_res_handler
      }
    }
  },
  can_handle = check_patched_device_models
}

return switch_patch_handler