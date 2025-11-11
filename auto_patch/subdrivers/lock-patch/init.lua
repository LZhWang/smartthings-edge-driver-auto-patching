local capabilities = require "st.capabilities"
local zcl_commands = require "st.zigbee.zcl.global_commands"
local clusters = require "st.zigbee.zcl.clusters"
local lock_patch = require "lock_patch"

-- import custom capabilities
local Language = capabilities["adminmusic34435.language"]
local LanguageCommandName = "setLanguage"
local AutoRelockTime = capabilities["adminmusic34435.autoRelockTime"]
local AutoRelockTimeCommandName = "setAutoRelockTime"
local SoundVolume = capabilities["adminmusic34435.soundVolume"]
local SoundVolumeCommandName = "setSoundVolume"
local OperatingMode = capabilities["adminmusic34435.operatingMode"]
local OperatingModeCommandName = "setOperatingMode"
local EnableOneTouchLocking = capabilities["adminmusic34435.enableOneTouchLocking"]
local EnableOneTouchLockingCommandName = "setEnableOneTouchLocking"
local EnableInsideStatusLED = capabilities["adminmusic34435.enableInsideStatusLed"]
local EnableInsideStatusLEDCommandName = "setEnableInsideStatusLED"
local EnablePrivacyModeButton = capabilities["adminmusic34435.enablePrivacyModeButton"]
local EnablePrivacyModeButtonCommandName = "setEnablePrivacyModeButton"
local WrongCodeEntryLimit = capabilities["adminmusic34435.wrongCodeEntryLimit"]
local WrongCodeEntryLimitCommandName = "setWrongCodeEntryLimit"
local UserCodeTemporaryDisableTime = capabilities["adminmusic34435.userCodeTemporaryDisableTime"]
local UserCodeTemporaryDisableTimeCommandName = "setUserCodeTemporaryDisableTime"

-- add more models if they also have these attributes
local PATCHED_DEVICE_MODELS = {
  { mfr = "Yale", model = "YRD226 TSDB" }
}

local check_patched_device_models = function(opts, driver, device)
  for _, fingerprint in ipairs(PATCHED_DEVICE_MODELS) do
      if device:get_model() == fingerprint.model then
          return true
      end
  end
  return false
end

CLUSTER_ID = clusters.DoorLock.ID
ATTR_IDS = {
  clusters.DoorLock.attributes.Language.ID,
  clusters.DoorLock.attributes.AutoRelockTime.ID,
  clusters.DoorLock.attributes.SoundVolume.ID,
  clusters.DoorLock.attributes.OperatingMode.ID,
  clusters.DoorLock.attributes.EnableOneTouchLocking.ID,
  clusters.DoorLock.attributes.EnableInsideStatusLED.ID,
  clusters.DoorLock.attributes.EnablePrivacyModeButton.ID,
  clusters.DoorLock.attributes.WrongCodeEntryLimit.ID,
  clusters.DoorLock.attributes.UserCodeTemporaryDisableTime.ID
}

local function device_init(driver, device)
  lock_patch.init_capability_values(device, CLUSTER_ID, ATTR_IDS, nil)
end


local yale_patched_handler = {
  NAME = "Yale lock patched Handler",
  lifecycle_handlers = {
    init = device_init,
  },
  capability_handlers = {
    [Language.ID] = { [LanguageCommandName] = lock_patch.language_capability_handler },
    [AutoRelockTime.ID] = { [AutoRelockTimeCommandName] = lock_patch.autorelocktime_capability_handler },
    [SoundVolume.ID] = { [SoundVolumeCommandName] = lock_patch.soundvolume_capability_handler },
    [OperatingMode.ID] = { [OperatingModeCommandName] = lock_patch.operatingmode_capability_handler },
    [EnableOneTouchLocking.ID] = { [EnableOneTouchLockingCommandName] = lock_patch.enableonetouchlocking_capability_handler },
    [EnableInsideStatusLED.ID] = { [EnableInsideStatusLEDCommandName] = lock_patch.enableinsidestatusled_capability_handler },
    [EnablePrivacyModeButton.ID] = { [EnablePrivacyModeButtonCommandName] = lock_patch.enableprivacymodebutton_capability_handler },
    [WrongCodeEntryLimit.ID] = { [WrongCodeEntryLimitCommandName] = lock_patch.wrongcodeentrylimit_capability_handler },
    [UserCodeTemporaryDisableTime.ID] = { [UserCodeTemporaryDisableTimeCommandName] = lock_patch.usercodetemporarydisabletime_capability_handler }
  },
  zigbee_handlers = {
    global = {
      [clusters.DoorLock.ID] = {
        [zcl_commands.WriteAttributeResponse.ID] = lock_patch.write_attr_res_handler,
        [zcl_commands.ReadAttributeResponse.ID] = lock_patch.read_attr_res_handler
      }
    }
  },
  can_handle = check_patched_device_models
}

return yale_patched_handler