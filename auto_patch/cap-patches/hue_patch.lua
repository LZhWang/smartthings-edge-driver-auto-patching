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
local PIROccupiedToUnoccupiedDelay = capabilities["adminmusic34435.pirOccupiedToUnoccupiedDelay"]
local HueMotionSensitivity = capabilities["adminmusic34435.hueMotionSensitivity"]


------------------------------------------------------ DO NOT MODIFY ------------------------------------------------
local hue_patch = {}

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
    if key == "PIROCCUPIEDTOUNOCCUPIEDDELAY_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(PIROccupiedToUnoccupiedDelay.PIROccupiedToUnoccupiedDelay(value))
        end
    elseif key == "HUEMOTIONSENSITIVITY_KEY" then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(HueMotionSensitivity.HueMotionSensitivity(value))
        end
    end
end
  
local function read_attr_res_handler(driver, device, zb_rx)
    for _,v in ipairs(zb_rx.body.zcl_body.attr_records) do
        attr_id = v.attr_id.value
        status = v.status.value
        if status == Status.SUCCESS then
            attr_value = v.data.value
            if attr_id == clusters.OccupancySensing.attributes.PIROccupiedToUnoccupiedDelay.ID then
                device:emit_event(PIROccupiedToUnoccupiedDelay.PIROccupiedToUnoccupiedDelay(attr_value))
            elseif attr_id == 0x0030 then
                device:emit_event(HueMotionSensitivity.HueMotionSensitivity(tostring(attr_value)))
            end
        end
    end
end

---------------- handle commands from ST app users' inputs ----------------
-- pir occupied to unoccupied delay
local function piroccupiedtounoccupieddelay_capability_handler(driver, device, command)
    local delay = command.args.delay
    set_pref_changed_field(device, "PIROCCUPIEDTOUNOCCUPIEDDELAY_KEY", delay)
    build_write_tx_message(device, clusters.OccupancySensing.ID, clusters.OccupancySensing.attributes.PIROccupiedToUnoccupiedDelay.ID, nil, data_types.Uint16.NAME, delay)
end

-- motion sensitivity
local function huemotionsensitivity_capability_handler(driver, device, command)
    local motionSensitivity = command.args.motionSensitivity
    set_pref_changed_field(device, "HUEMOTIONSENSITIVITY_KEY", motionSensitivity)
    build_write_tx_message(device, clusters.OccupancySensing.ID, 0x0030, 0x100B, data_types.Uint8.NAME, tonumber(motionSensitivity))
end

hue_patch.init_capability_values = init_capability_values
hue_patch.write_attr_res_handler = write_attr_res_handler
hue_patch.read_attr_res_handler = read_attr_res_handler

hue_patch.piroccupiedtounoccupieddelay_capability_handler = piroccupiedtounoccupieddelay_capability_handler
hue_patch.huemotionsensitivity_capability_handler = huemotionsensitivity_capability_handler

return hue_patch
