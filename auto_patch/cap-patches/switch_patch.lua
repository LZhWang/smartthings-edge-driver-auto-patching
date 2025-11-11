local capabilities = require "st.capabilities"
local zcl_commands = require "st.zigbee.zcl.global_commands"
local clusters = require "st.zigbee.zcl.clusters"
local data_types = require "st.zigbee.data_types"
local zcl_messages = require "st.zigbee.zcl"
local zb_const = require "st.zigbee.constants"
local messages = require "st.zigbee.messages"
local write_attribute = require "st.zigbee.zcl.global_commands.write_attribute"
local read_attribute = require "st.zigbee.zcl.global_commands.read_attribute"
local Status = (require "st.zigbee.zcl.types").ZclStatus

-- import custom capabilities
local IdentifyTime = capabilities["adminmusic34435.identifyTime"]
local DeviceEnabled = capabilities["adminmusic34435.deviceEnabled"]
local OnOffTransitionTime = capabilities["adminmusic34435.onOffTransitionTime"]
local OnLevel = capabilities["adminmusic34435.onLevel"]
local OnTime = capabilities["adminmusic34435.onTime"]
local OffWaitTime = capabilities["adminmusic34435.offWaitTime"]
local StartUpOnOff = capabilities["adminmusic34435.startUpOnOff"]
local StartUpColorTemperatureMireds = capabilities["adminmusic34435.startUpColorTemperatureMireds"]

------------------------------------------------------ DO NOT MODIFY ------------------------------------------------
local switch_patch = {}

local PREF_CHANGED_KEY = "prefChangedKey"
local PREF_CHANGED_VALUE = "prefChangedValue"

local function get_pref_changed_field(device)
    local key = device:get_field(PREF_CHANGED_KEY) or ''
    local value = device:get_field(PREF_CHANGED_VALUE) or 0
    return key, value
end

local function set_pref_changed_field(device, key, value)
    device:set_field(PREF_CHANGED_KEY, key)
    device:set_field(PREF_CHANGED_VALUE, value)
end

-- Build the complete ZCL message and send it to the device
local function build_zcl_message(device,cluster_id,zclh,body_message,mfg_specific_code)
    local addrh = messages.AddressHeader(
        zb_const.HUB.ADDR,
        zb_const.HUB.ENDPOINT,
        device:get_short_address(),
        device:get_endpoint(cluster_id),
        zb_const.HA_PROFILE_ID,
        cluster_id
    )
    local message_body = zcl_messages.ZclMessageBody({
        zcl_header = zclh,
        zcl_body = body_message
    })
    local txMessage = messages.ZigbeeMessageTx({
        address_header = addrh,
        body = message_body
    })
    --Add the manufacturer info if exists
    if mfg_specific_code then
        txMessage.body.zcl_header.frame_ctrl:set_mfg_specific()
        txMessage.body.zcl_header.mfg_code = data_types.validate_or_build_type(mfg_specific_code, data_types.Uint16, "mfg_code")
    end
    device:send(txMessage)
end
  
--Function to write a cluster attribute
local function build_write_tx_message(device, cluster_id, attr_id, mfg_specific_code, attr_type, attr_value)
    local zclh = zcl_messages.ZclHeader({
        cmd = data_types.ZCLCommandId(write_attribute.WriteAttribute.ID)
    })
    local attr_write = write_attribute.WriteAttributeAttributeRecord(
        data_types.AttributeId(attr_id),
        data_types.ZigbeeDataType(data_types[attr_type].ID),
        data_types[attr_type](attr_value)
    )
    local write_body = write_attribute.WriteAttribute({ attr_write })
    build_zcl_message(device,cluster_id,zclh,write_body,mfg_specific_code)
end


-- Function to read a cluster attribute, attr_ids is a list of attributes to be read
local function build_read_tx_message(device, cluster_id, attr_ids, mfg_specific_code)
    local zclh = zcl_messages.ZclHeader({
        cmd = data_types.ZCLCommandId(read_attribute.ReadAttribute.ID)
    })
    local read_body = read_attribute.ReadAttribute(attr_ids)
    build_zcl_message(device,cluster_id,zclh,read_body,mfg_specific_code)
end

-- initialize capability values by sending read attribute commands 
local function init_capability_values(device, cluster_id, attr_ids, mfg_specific_code)
    build_read_tx_message(device, cluster_id, attr_ids, mfg_specific_code)
end

------------------------------------------------------ DO NOT MODIFY ------------------------------------------------

local function write_attr_res_handler(driver, device, zb_rx)
    local key, value = get_pref_changed_field(device)
    if key == "IDENTIFYTIME_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(IdentifyTime.IdentifyTime(value))
        end
    elseif key == "DEVICEENABLED_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(DeviceEnabled.DeviceEnabled(value))
        end
    elseif key == "ONOFFTRANSITIONTIME_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(OnOffTransitionTime.OnOffTransitionTime(value))
        end
    elseif key == "ONLEVEL_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(OnLevel.OnLevel(value))
        end
    elseif key == "ONTIME_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(OnTime.OnTime(value))
        end
    elseif key == "OFFWAITTIME_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(OffWaitTime.OffWaitTime(value))
        end
    elseif key == "STARTUPONOFF_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(StartUpOnOff.StartUpOnOff(value))
        end
    elseif key == "STARTUPCOLORTEMPERATUREMIREDS_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(StartUpColorTemperatureMireds.StartUpColorTemperatureMireds(value))
        end
    end
end
  
local function read_attr_res_handler(driver, device, zb_rx)
    for _,v in ipairs(zb_rx.body.zcl_body.attr_records) do
        status = v.status.value
        if status == Status.SUCCESS then
            attr_value = v.data.value
            attr_name = v.data.field_name
            if attr_name == "IdentifyTime" then
                device:emit_event(IdentifyTime.IdentifyTime(attr_value))
            elseif attr_name == "DeviceEnabled" then
                attr_value = (attr_value == true and 'enabled') or (attr_value == false and 'disabled')
                device:emit_event(DeviceEnabled.DeviceEnabled(attr_value))
            elseif attr_name == "OnOffTransitionTime" then
                device:emit_event(OnOffTransitionTime.OnOffTransitionTime(attr_value))
            elseif attr_name == "OnLevel" then
                device:emit_event(OnLevel.OnLevel(attr_value))
            elseif attr_name == "OnTime" then
                device:emit_event(OnTime.OnTime(attr_value))
            elseif attr_name == "OffWaitTime" then
                device:emit_event(OffWaitTime.OffWaitTime(attr_value))
            elseif attr_name == "StartUpOnOff" then
                device:emit_event(StartUpOnOff.StartUpOnOff(tostring(attr_value)))
            elseif attr_name == "StartUpColorTemperatureMireds" then
                device:emit_event(StartUpColorTemperatureMireds.StartUpColorTemperatureMireds(attr_value)) 
            end
        end
    end
end

---------------- handle commands from ST app users' inputs ----------------
-- Identify: identify time
local function identifytime_capability_handler(driver, device, command)
    local identifyTime = command.args.identifyTime
    set_pref_changed_field(device, "IDENTIFYTIME_KEY", identifyTime)
    build_write_tx_message(device, clusters.Identify.ID, clusters.Identify.attributes.IdentifyTime.ID, nil, data_types.Uint16.NAME, identifyTime)
end

-- Basic: device enabled
local function deviceenabled_capability_handler(driver, device, command)
    local deviceEnabled = command.args.deviceEnabled
    set_pref_changed_field(device, "DEVICEENABLED_KEY", deviceEnabled)
    deviceEnabled = (deviceEnabled == 'enabled' and true) or (deviceEnabled == 'disabled' and false)
    build_write_tx_message(device, clusters.Basic.ID, clusters.Basic.attributes.DeviceEnabled.ID, nil, data_types.Boolean.NAME, deviceEnabled)
end

-- Level (Control): on off transition time
local function onofftransitiontime_capability_handler(driver, device, command)
    local onOffTransitionTime = command.args.onOffTransitionTime
    set_pref_changed_field(device, "ONOFFTRANSITIONTIME_KEY", onOffTransitionTime)
    build_write_tx_message(device, clusters.Level.ID, clusters.Level.attributes.OnOffTransitionTime.ID, nil, data_types.Uint16.NAME, onOffTransitionTime)
end

-- Level (Control): on level
local function onlevel_capability_handler(driver, device, command)
    local onLevel = command.args.onLevel
    set_pref_changed_field(device, "ONLEVEL_KEY", onLevel)
    build_write_tx_message(device, clusters.Level.ID, clusters.Level.attributes.OnLevel.ID, nil, data_types.Uint8.NAME, onLevel)
end

-- OnOff: on time
local function ontime_capability_handler(driver, device, command)
    local onTime = command.args.onTime
    set_pref_changed_field(device, "ONTIME_KEY", onTime)
    build_write_tx_message(device, clusters.OnOff.ID, clusters.OnOff.attributes.OnTime.ID, nil, data_types.Uint16.NAME, onTime)
end

-- OnOff: off wait time
local function offwaittime_capability_handler(driver, device, command)
    local offWaitTime = command.args.offWaitTime
    set_pref_changed_field(device, "OFFWAITTIME_KEY", offWaitTime)
    build_write_tx_message(device, clusters.OnOff.ID, clusters.OnOff.attributes.OffWaitTime.ID, nil, data_types.Uint16.NAME, offWaitTime)
end

-- OnOff: start up on off
local function startuponoff_capability_handler(driver, device, command)
    local startUpOnOff = command.args.startUpOnOff
    set_pref_changed_field(device, "STARTUPONOFF_KEY", startUpOnOff)
    build_write_tx_message(device, clusters.OnOff.ID, clusters.OnOff.attributes.StartUpOnOff.ID, nil, data_types.Enum8.NAME, tonumber(startUpOnOff))
end

-- ColorControl: start up color temperature mireds
local function startupcolortemperaturemireds_capability_handler(driver, device, command)
    local startUpColorTemperatureMireds = command.args.startUpColorTemperatureMireds
    set_pref_changed_field(device, "STARTUPCOLORTEMPERATUREMIREDS_KEY", startUpColorTemperatureMireds)
    build_write_tx_message(device, clusters.ColorControl.ID, clusters.ColorControl.attributes.StartUpColorTemperatureMireds.ID, nil, data_types.Uint16.NAME, startUpColorTemperatureMireds)
end

switch_patch.init_capability_values = init_capability_values
switch_patch.write_attr_res_handler = write_attr_res_handler
switch_patch.read_attr_res_handler = read_attr_res_handler

switch_patch.identifytime_capability_handler = identifytime_capability_handler
switch_patch.deviceenabled_capability_handler = deviceenabled_capability_handler
switch_patch.onofftransitiontime_capability_handler = onofftransitiontime_capability_handler
switch_patch.onlevel_capability_handler = onlevel_capability_handler
switch_patch.ontime_capability_handler = ontime_capability_handler
switch_patch.offwaittime_capability_handler = offwaittime_capability_handler
switch_patch.startuponoff_capability_handler = startuponoff_capability_handler
switch_patch.startupcolortemperaturemireds_capability_handler = startupcolortemperaturemireds_capability_handler

return switch_patch
