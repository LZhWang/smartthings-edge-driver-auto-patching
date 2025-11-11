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
local Language = capabilities["adminmusic34435.language"]
local AutoRelockTime = capabilities["adminmusic34435.autoRelockTime"]
local SoundVolume = capabilities["adminmusic34435.soundVolume"]
local OperatingMode = capabilities["adminmusic34435.operatingMode"]
local EnableOneTouchLocking = capabilities["adminmusic34435.enableOneTouchLocking"]
local EnableInsideStatusLED = capabilities["adminmusic34435.enableInsideStatusLed"]
local EnablePrivacyModeButton = capabilities["adminmusic34435.enablePrivacyModeButton"]
local WrongCodeEntryLimit = capabilities["adminmusic34435.wrongCodeEntryLimit"]
local UserCodeTemporaryDisableTime = capabilities["adminmusic34435.userCodeTemporaryDisableTime"]


------------------------------------------------------ DO NOT MODIFY ------------------------------------------------
local lock_patch = {}

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
local function build_zcl_message(device, cluster_id, zclh, body_message, mfg_specific_code)
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
    -- add more keys for other attributes
    if key == 'LANGUAGE_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(Language.Language(value))
        end
    elseif key == 'AUTORELOCKTIME_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(AutoRelockTime.AutoRelockTime(value))
        end
    elseif key == 'SOUNDVOLUME_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(SoundVolume.SoundVolume(value))
        end
    elseif key == 'OPERATINGMODE_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(OperatingMode.OperatingMode(value))
        end
    elseif key == 'ENABLEONETOUCHLOCKING_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(EnableOneTouchLocking.EnableOneTouchLocking(value))
        end
    elseif key == 'ENABLEINSIDESTATUSLED_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(EnableInsideStatusLED.EnableInsideStatusLED(value))
        end
    elseif key == 'ENABLEPRIVACYMODEBUTTON_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(EnablePrivacyModeButton.EnablePrivacyModeButton(value))
        end
    elseif key == 'WRONGCODEENTRYLIMIT_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(WrongCodeEntryLimit.WrongCodeEntryLimit(value))
        end
    elseif key == 'USERCODETEMPORARYDISABLETIME_KEY' then
        set_pref_changed_field(device, '', 0)
        if zb_rx.body.zcl_body.global_status.value == Status.SUCCESS then
            device:emit_event(UserCodeTemporaryDisableTime.UserCodeTemporaryDisableTime(value))
        end
    end
end

local function read_attr_res_handler(driver, device, zb_rx)
    for _,v in ipairs(zb_rx.body.zcl_body.attr_records) do
        attr_id = v.attr_id.value
        status = v.status.value
        if status == Status.SUCCESS then
            --attr_data_type = v.data_type.value
            attr_value = v.data.value
            if attr_id == clusters.DoorLock.attributes.Language.ID then
                device:emit_event(Language.Language(attr_value))
            elseif attr_id == clusters.DoorLock.attributes.AutoRelockTime.ID then
                device:emit_event(AutoRelockTime.AutoRelockTime(attr_value))
            elseif attr_id == clusters.DoorLock.attributes.SoundVolume.ID then
                device:emit_event(SoundVolume.SoundVolume(tostring(attr_value)))
            elseif attr_id == clusters.DoorLock.attributes.OperatingMode.ID then
                device:emit_event(OperatingMode.OperatingMode(tostring(attr_value)))
            elseif attr_id == clusters.DoorLock.attributes.EnableOneTouchLocking.ID then
                attr_value = (attr_value == true and 'enabled') or (attr_value == false and 'disabled')
                device:emit_event(EnableOneTouchLocking.EnableOneTouchLocking(attr_value))
            elseif attr_id == clusters.DoorLock.attributes.EnableInsideStatusLED.ID then
                attr_value = (attr_value == true and 'enabled') or (attr_value == false and 'disabled')
                device:emit_event(EnableInsideStatusLED.EnableInsideStatusLED(attr_value))
            elseif attr_id == clusters.DoorLock.attributes.EnablePrivacyModeButton.ID then
                attr_value = (attr_value == true and 'enabled') or (attr_value == false and 'disabled')
                device:emit_event(EnablePrivacyModeButton.EnablePrivacyModeButton(attr_value))
            elseif attr_id == clusters.DoorLock.attributes.WrongCodeEntryLimit.ID then
                device:emit_event(WrongCodeEntryLimit.WrongCodeEntryLimit(attr_value))
            elseif attr_id == clusters.DoorLock.attributes.UserCodeTemporaryDisableTime.ID then
                device:emit_event(UserCodeTemporaryDisableTime.UserCodeTemporaryDisableTime(attr_value))
            end
        end
    end
end

---------------- handle commands from ST app users' inputs ----------------
-- language
local function language_capability_handler(driver, device, command)
    local language = command.args.language
    set_pref_changed_field(device, 'LANGUAGE_KEY', language)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.Language.ID, nil, data_types.CharString.NAME, language)
end

-- auto relock time
local function autorelocktime_capability_handler(driver, device, command)
    local relockTime = command.args.relockTime
    set_pref_changed_field(device, 'AUTORELOCKTIME_KEY', relockTime)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.AutoRelockTime.ID, nil, data_types.Uint32.NAME, relockTime)
end

-- sound volume
local function soundvolume_capability_handler(driver, device, command)
    local soundVolume = command.args.soundVolume
    set_pref_changed_field(device, 'SOUNDVOLUME_KEY', soundVolume)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.SoundVolume.ID, nil, data_types.Uint8.NAME, tonumber(soundVolume))
end

-- operating mode
local function operatingmode_capability_handler(driver, device, command)
    local operatingMode = command.args.operatingMode
    set_pref_changed_field(device, 'OPERATINGMODE_KEY', operatingMode)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.OperatingMode.ID, nil, data_types.Enum8.NAME, tonumber(operatingMode))
end

-- enable one touch locking
local function enableonetouchlocking_capability_handler(driver, device, command)
    local oneTouchLocking = command.args.oneTouchLocking
    set_pref_changed_field(device, 'ENABLEONETOUCHLOCKING_KEY', oneTouchLocking)
    oneTouchLocking = (oneTouchLocking == 'enabled' and true) or (oneTouchLocking == 'disabled' and false)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.EnableOneTouchLocking.ID, nil, data_types.Boolean.NAME, oneTouchLocking)
end

-- enable inside status led
local function enableinsidestatusled_capability_handler(driver, device, command)
    local insideStatusLED = command.args.insideStatusLED
    set_pref_changed_field(device, 'ENABLEINSIDESTATUSLED_KEY', insideStatusLED)
    insideStatusLED = (insideStatusLED == 'enabled' and true) or (insideStatusLED == 'disabled' and false)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.EnableInsideStatusLED.ID, nil, data_types.Boolean.NAME, insideStatusLED)
end

-- enable privacy mode button
local function enableprivacymodebutton_capability_handler(driver, device, command)
    local privacyModeButton = command.args.privacyModeButton
    set_pref_changed_field(device, 'ENABLEPRIVACYMODEBUTTON_KEY', privacyModeButton)
    privacyModeButton = (privacyModeButton == 'enabled' and true) or (privacyModeButton == 'disabled' and false)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.EnablePrivacyModeButton.ID, nil, data_types.Boolean.NAME, privacyModeButton)
end

-- wrong code entry limit
local function wrongcodeentrylimit_capability_handler(driver, device, command)
    local entryLimit = command.args.entryLimit
    set_pref_changed_field(device, 'WRONGCODEENTRYLIMIT_KEY', entryLimit)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.WrongCodeEntryLimit.ID, nil, data_types.Uint8.NAME, entryLimit)
end

-- user code temporary disable time
local function usercodetemporarydisabletime_capability_handler(driver, device, command)
    local disableTime = command.args.disableTime
    set_pref_changed_field(device, 'USERCODETEMPORARYDISABLETIME_KEY', disableTime)
    build_write_tx_message(device, clusters.DoorLock.ID, clusters.DoorLock.attributes.UserCodeTemporaryDisableTime.ID, nil, data_types.Uint8.NAME, disableTime)
end


lock_patch.init_capability_values = init_capability_values
lock_patch.write_attr_res_handler = write_attr_res_handler
lock_patch.read_attr_res_handler = read_attr_res_handler

lock_patch.language_capability_handler = language_capability_handler
lock_patch.autorelocktime_capability_handler = autorelocktime_capability_handler
lock_patch.soundvolume_capability_handler = soundvolume_capability_handler
lock_patch.operatingmode_capability_handler = operatingmode_capability_handler
lock_patch.enableonetouchlocking_capability_handler = enableonetouchlocking_capability_handler
lock_patch.enableinsidestatusled_capability_handler = enableinsidestatusled_capability_handler
lock_patch.enableprivacymodebutton_capability_handler = enableprivacymodebutton_capability_handler
lock_patch.wrongcodeentrylimit_capability_handler = wrongcodeentrylimit_capability_handler
lock_patch.usercodetemporarydisabletime_capability_handler = usercodetemporarydisabletime_capability_handler

return lock_patch