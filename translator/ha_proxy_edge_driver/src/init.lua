-- Home Assistant Proxy Edge Driver
local log = require "log"
-- local Driver = require "st.driver" -- uncomment in real Edge environment
-- local capabilities = require "st.capabilities"
local ha_proxy = require "ha_proxy"

local CONFIG_PATH = os.getenv("HA_EDGE_CONFIG_PATH") or "../config/ha_devices.yaml"

local DRIVER_NAME = "HA Proxy Edge Driver"

-- Minimal capability handler stubs (replace with real st.capabilities)
local capabilities = {
  switch = { ID = "switch" },
  switchLevel = { ID = "switchLevel" },
  lock = { ID = "lock" },
  contactSensor = { ID = "contactSensor" },
  motionSensor = { ID = "motionSensor" }
}

local function command_handler(driver, device, cmd)
  log.info(string.format("Received command %s for %s", cmd.command, device.device_network_id))
  local ok, err = ha_proxy.call_service(device, cmd.capability, cmd.command, cmd.args)
  if not ok then
    log.error(string.format("Command failed: %s", err or "unknown"))
  end
end

local function remember_entity(device)
  -- In a real Edge driver, the network ID should be set to the HA entity_id.
  local ha_entity_id = device.device_network_id
  if device.set_field then
    device:set_field("ha_entity_id", ha_entity_id, { persist = true })
  end
end

local function device_init(driver, device)
  log.info(string.format("Initializing device %s", device.device_network_id))
  remember_entity(device)
  -- Optionally refresh state on init
  ha_proxy.refresh_state(device)
end

local function device_added(driver, device)
  log.info(string.format("Device added %s", device.device_network_id))
  remember_entity(device)
end

-- Driver template (pseudocode as st.driver not available in this environment)
local driver_template = {
  name = DRIVER_NAME,
  lifecycle_handlers = {
    init = device_init,
    added = device_added,
  },
  capability_handlers = {
    [capabilities.switch.ID] = {
      on = command_handler,
      off = command_handler,
    },
    [capabilities.switchLevel.ID] = {
      setLevel = command_handler,
    },
    [capabilities.lock.ID] = {
      lock = command_handler,
      unlock = command_handler,
    },
  },
}

local function main()
  ha_proxy.init(CONFIG_PATH)
  -- In a real Edge driver:
  -- local driver = Driver(driver_template)
  -- driver:run()
  log.info("Driver initialized (stub). Replace with st.driver to run on hub.")
end

main()
