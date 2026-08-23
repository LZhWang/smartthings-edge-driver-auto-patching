-- Helper functions for talking to Home Assistant from the Edge driver
local yaml = require "lyaml" -- ensure available in Edge runtime or replace
local http = require "socket.http" -- simple HTTP; replace with ST LAN libs as needed
local ltn12 = require "ltn12"
local json = require "dkjson"

local log = require "log"
local os = os

local M = {
  config = nil,
  devices = {},
}

local function load_config(path)
  local fh, err = io.open(path, "r")
  if not fh then
    return nil, ("Failed to read config %s: %s"):format(path, err)
  end
  local content = fh:read("*a")
  fh:close()
  local ok, data = pcall(yaml.load, content)
  if not ok then
    return nil, ("Failed to parse YAML: %s"):format(data)
  end
  return data, nil
end

local function env_or_config(env_key, cfg_key, cfg)
  return os.getenv(env_key) or cfg[cfg_key]
end

function M.init(config_path)
  local cfg, err = load_config(config_path)
  if not cfg then
    log.error(err)
    return false, err
  end
  cfg.ha_base_url = env_or_config("HA_EDGE_BASE_URL", "ha_base_url", cfg)
  cfg.ha_token = env_or_config("HA_EDGE_TOKEN", "ha_token", cfg)
  M.config = cfg
  local devices = cfg.devices or {}
  for _, d in ipairs(devices) do
    M.devices[d.ha_entity_id] = d
  end
  log.info(string.format("Loaded %d HA devices from config", #devices))
  return true
end

local function build_headers(token)
  local headers = { ["Content-Type"] = "application/json" }
  if token then
    headers["Authorization"] = "Bearer " .. token
  end
  return headers
end

local function entity_domain(entity_id)
  if not entity_id then return nil end
  local dot = string.find(entity_id, ".", 1, true)
  if not dot or dot == 1 then return nil end
  return string.sub(entity_id, 1, dot - 1)
end

local function domain_service_from_capability(capability, command, ha_entity_id)
  local domain = entity_domain(ha_entity_id)
  if capability == "switch" then
    return domain or "switch", command == "on" and "turn_on" or "turn_off"
  end
  if capability == "switchLevel" then
    return domain or "light", "turn_on"
  end
  if capability == "lock" then
    return "lock", command
  end
  if capability == "contactSensor" or capability == "motionSensor" then
    return nil, nil -- read-only
  end
  return nil, nil
end

function M.call_service(device, capability, command, args)
  local ha_entity_id = device.device_network_id or (device.get_field and device:get_field("ha_entity_id"))
  local domain, service = domain_service_from_capability(capability, command, ha_entity_id)
  if not domain or not service then
    return false, "Unsupported capability/command"
  end

  local url = string.format("%s/api/services/%s/%s", M.config.ha_base_url, domain, service)
  local payload = { entity_id = ha_entity_id }

  if capability == "switchLevel" and args and args.level then
    payload.brightness = args.level
  end

  local body = json.encode(payload)
  local resp_body = {}
  local _, code = http.request{
    url = url,
    method = "POST",
    headers = build_headers(M.config.ha_token),
    source = ltn12.source.string(body),
    sink = ltn12.sink.table(resp_body),
  }
  if code ~= 200 and code ~= 201 and code ~= 202 then
    return false, "HA service call failed with HTTP " .. tostring(code)
  end
  return true
end

function M.refresh_state(device)
  local ha_entity_id = device.device_network_id or (device.get_field and device:get_field("ha_entity_id"))
  local url = string.format("%s/api/states/%s", M.config.ha_base_url, ha_entity_id)
  local resp_body = {}
  local _, code = http.request{
    url = url,
    method = "GET",
    headers = build_headers(M.config.ha_token),
    sink = ltn12.sink.table(resp_body),
  }
  if code ~= 200 then
    log.warn(string.format("Refresh failed for %s: HTTP %s", ha_entity_id, tostring(code)))
    return
  end
  -- In real driver, parse JSON and emit capability events based on state.
  log.debug(string.format("Refresh response: %s", table.concat(resp_body)))
end

return M
