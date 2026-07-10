# esp32-blackbox

Surveillance / security node built on the shared `nayaka-nms` ESP32 framework
(WiFi FSM, MQTT with NVS-persisted config, ElegantOTA + MQTT-pull OTA, task
watchdog, LED diagnostics, serial console). It fuses three subsystems onto one
device:

- **Door** — magnetic reed switch (open / closed).
- **Mains (PLN)** — optocoupler sensing grid power presence (the node is
  battery/UPS-backed, so a mains loss is reported in real time).
- **Motion** — 3× PIR sensors.
- **Rotary beacon** — a relay-driven warning light, **controlled remotely over
  MQTT only** (the firmware never auto-triggers it).

Inputs are **event-driven**: each debounced change (both edges) publishes
immediately, and a full **snapshot** of every subsystem is published every
60 s (and once at boot) so the backend always has recent ground truth.

## Hardware / pin map

| Function | GPIO | Mode | Convention |
|---|---|---|---|
| Door reed | 27 | `INPUT_PULLUP` | LOW = closed, HIGH = open |
| Mains (PLN) | 32 | `INPUT` | LOW = present, HIGH = lost (`POWER_ACTIVE_LOW`) |
| PIR 1 | 33 | `INPUT` | HIGH = motion |
| PIR 2 | 35 | `INPUT` (input-only) | HIGH = motion |
| PIR 3 | 34 | `INPUT` (input-only) | HIGH = motion |
| Relay (rotary beacon) | 26 | `OUTPUT` | `RELAY_ACTIVE_HIGH`, boots OFF |
| Diagnostic LED | 2 | `OUTPUT` | framework status blinks |

Active levels and debounce times are configurable in `config.h`
(`POWER_ACTIVE_LOW`, `RELAY_ACTIVE_HIGH`, `DEBOUNCE_*_MS`).

## Source layout

| File | Role |
|---|---|
| `blackbox.ino` | entry sketch (`setup`/`loop`) |
| `config.h` | identity, pins, cadences, topics, NVS keys |
| `sensor.{h,ino}` | door / mains / PIR input driver (debounce + both-edge) |
| `relay.{h,ino}` | rotary beacon output (remote control + auto-off) |
| `payload.ino` | event publish + periodic snapshot |
| `system.ino` | framework + blackbox `relay` / `pir` config verbs |
| `ota.{h,ino}` | ElegantOTA + HTTP-pull OTA (unchanged framework) |

## Build

- Arduino IDE 2.x, ESP32 Arduino core ≥ 3.0 (ESP-IDF 5.x), Board: *ESP32 Dev Module*.
- Libraries: `PubSubClient`, `ArduinoJson v7`, `ESPAsyncWebServer` + `AsyncTCP`, `ElegantOTA v3`.

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 surveillance/blackbox
```

## Defaults

| Key | Default |
|---|---|
| Client ID | `esp32-blackbox-<mac12-lowercase>` |
| Scan / poll cadence | `100 ms` (`DEF_INTERVAL_MS`, range 50 ms – 24 h) |
| Snapshot | `60 s` (`SNAPSHOT_INTERVAL_MS`) |
| Heartbeat | `5 min` (fixed) |
| Watchdog | `60 s` (panic + reset) |
| Offline-restart | MQTT down for `10 min` ⇒ auto-restart |
| Relay auto-off cap | `1 h` (`RELAY_MAX_TIMEOUT_MS`) |

## MQTT topics

All scoped under `nms/<client_id>/blackbox/`.

| Direction | Topic | Cadence |
|---|---|---|
| publish | `…/door` | on edge + snapshot |
| publish | `…/device_power` | on edge + snapshot |
| publish | `…/motion_pir` | on edge + snapshot |
| publish | `…/relay_rotary` | on command / auto-off + snapshot |
| publish | `…/heartbeat` | every 5 min |
| publish | `…/info` | once per connect (retained) |
| subscribe | `…/config` | inbound config / commands |
| publish | `…/config/response` | acks |
| subscribe | `…/audit` | inbound audit |
| publish | `…/audit/response` | audit reply |
| publish | `…/ota/status` | OTA progress |

### Data payloads (envelope adds `ip`, `ts`)

```json
{ "ip": "192.168.1.50", "ts": 12345678, "open": true }
```
```json
{ "ip": "192.168.1.50", "ts": 12345678, "mains": false }
```
```json
{ "ip": "192.168.1.50", "ts": 12345678, "s": [1, 0, null] }
```
- `door.open` — `true` = open. `device_power.mains` — `true` = grid present.
- `motion_pir.s[i]` — `1` = motion, `0` = clear, `null` = channel disabled.

```json
{ "ip": "192.168.1.50", "ts": 12345678, "state": true, "source": "mqtt" }
```
- `relay_rotary.source` — `"mqtt"` (commanded), `"timeout"` (auto-off), `"snapshot"`.

## Config commands (publish to `…/config`)

```jsonc
// Rotary beacon — remote control (blackbox-only)
{"relay": {"state": true}}                       // latch ON
{"relay": {"state": true, "timeout_ms": 30000}}  // ON, auto-OFF after 30 s
{"relay": {"state": false}}                      // latch OFF

// PIR per-channel enable (blackbox-only)
{"pir": {"ch": 0, "enabled": false}}             // ch 0..2, persisted in NVS

// Framework verbs
{"wifi": {"ssid": "...", "pass": "..."}}
{"mqtt": {"host": "...", "port": 1883, "user": "...", "pass": "...", "client_id": "..."}}
{"interval": {"delay_ms": 100}}                  // scan cadence (50..86400000 ms)
{"reset": {"action": true}}
{"ota": {"url": "http://host/firmware.bin", "md5": "<optional>"}}
{"factory_reset": {"action": true}}
```

Acks go to `…/config/response` as `{ "config_<key>": { "status": "success" | "failed" } }`
(e.g. `config_relay`, `config_pir`).

## Audit commands (publish to `…/audit`)

```jsonc
{"last_config": {}}   // current config (passwords redacted)
{"heartbeat": {}}     // IP + uptime + fw
{"info": {}}          // fw / project / build / mac / client_id
```

## Serial console (115200 8N1)

| Command | Purpose |
|---|---|
| `STATUS` / `VERSION` / `HEARTBEAT` / `CONFIG` | reports |
| `WIFI {...}` / `MQTT {...}` / `INTERVAL {...}` | provisioning (restart) |
| `RELAY {"state":true,"timeout_ms":30000}` | drive the beacon |
| `PIR {"ch":0,"enabled":false}` | enable/disable a PIR channel |
| `OTA {"url":"...","md5":"..."}` | trigger HTTP firmware pull |
| `RESET` / `FACTORY_RESET {"action":true}` | restart / wipe NVS |

## LED indicator (`GPIO2`)

| Blinks | Meaning |
|---|---|
| 1× | Publish OK |
| 2× | MQTT publish / connect failed |
| 3× | WiFi connect failed |

## OTA

- **Web UI**: `http://<device-ip>/update` (ElegantOTA, no auth).
- **MQTT pull**: `{"ota": {"url": "http://host/firmware.bin"}}` → `…/config`.

Both pause input publishing (`otaIsActive()`); device reboots on success.

## Verification

```bash
mosquitto_sub -h <broker> -t 'nms/+/blackbox/#' -v
```

1. Provision over serial: `WIFI {...}`, `MQTT {...}`.
2. Open/close the door, wave at each PIR, drop mains → expect an immediate event
   on the matching topic per edge, plus a snapshot within 60 s.
3. Drive the beacon and confirm auto-off:
   ```bash
   mosquitto_pub -h <broker> -t nms/<cid>/blackbox/config \
     -m '{"relay":{"state":true,"timeout_ms":5000}}'
   ```
   → relay energises, `relay_rotary` publishes `source:"mqtt"`, then auto-offs
   after 5 s with `source:"timeout"`.
4. Reboot → relay comes up OFF; disabled PIR channels stay disabled.
