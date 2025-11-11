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
local CheckInInterval = capabilities["adminmusic34435.checkInInterval"]
local FastPollTimeout = capabilities["adminmusic34435.fastPollTimeout"]
local IdentifyTime = capabilities["adminmusic34435.identifyTime"]
local DeviceEnabled = capabilities["adminmusic34435.deviceEnabled"]

------------------------------------------------------ DO NOT MODIFY ------------------------------------------------
local button_patch = {}

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
    if key == "CHECKININTERVAL_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(CheckInInterval.CheckInInterval(value))
        end
    elseif key == "FASTPOLLTIMEOUT_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(FastPollTimeout.FastPollTimeout(value))
        end
    elseif key == "IDENTIFYTIME_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(IdentifyTime.IdentifyTime(value))
        end
    elseif key == "DEVICEENABLED_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(DeviceEnabled.DeviceEnabled(value))
        end
    end
end
  
local function read_attr_res_handler(driver, device, zb_rx)
    for _,v in ipairs(zb_rx.body.zcl_body.attr_records) do
        status = v.status.value
        if status == Status.SUCCESS then
            --attr_data_type = v.data_type.value
            attr_value = v.data.value
            attr_name = v.data.field_name
            if attr_name == "CheckInInterval" then
                device:emit_event(CheckInInterval.CheckInInterval(attr_value))
            elseif attr_name == "FastPollTimeout" then
                device:emit_event(FastPollTimeout.FastPollTimeout(attr_value))
            elseif attr_name == "IdentifyTime" then
                device:emit_event(IdentifyTime.IdentifyTime(attr_value))
            elseif attr_name == "DeviceEnabled" then
                attr_value = (attr_value == true and 'enabled') or (attr_value == false and 'disabled')
                device:emit_event(DeviceEnabled.DeviceEnabled(attr_value))
            end
        end
    end
end

---------------- handle commands from ST app users' inputs ----------------
-- PollControl: check in interval
local function checkininterval_capability_handler(driver, device, command)
    local checkInInterval = command.args.checkInInterval
    set_pref_changed_field(device, "CHECKININTERVAL_KEY", checkInInterval)
    build_write_tx_message(device, clusters.PollControl.ID, clusters.PollControl.attributes.CheckInInterval.ID, nil, data_types.Uint32.NAME, checkInInterval)
end

-- PollControl: fast poll timeout
local function fastpolltimeout_capability_handler(driver, device, command)
    local fastPollTimeout = command.args.fastPollTimeout
    set_pref_changed_field(device, "FASTPOLLTIMEOUT_KEY", fastPollTimeout)
    build_write_tx_message(device, clusters.PollControl.ID, clusters.PollControl.attributes.FastPollTimeout.ID, nil, data_types.Uint16.NAME, fastPollTimeout)
end

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

button_patch.init_capability_values = init_capability_values
button_patch.write_attr_res_handler = write_attr_res_handler
button_patch.read_attr_res_handler = read_attr_res_handler

button_patch.checkininterval_capability_handler = checkininterval_capability_handler
button_patch.fastpolltimeout_capability_handler = fastpolltimeout_capability_handler
button_patch.identifytime_capability_handler = identifytime_capability_handler
button_patch.deviceenabled_capability_handler = deviceenabled_capability_handler

return button_patch
