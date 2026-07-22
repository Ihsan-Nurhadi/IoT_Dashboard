# esp32-speaker

A surveillance-fleet ESP32 node that drives a **JQ6500 MP3 module** as a
remote-commanded announcement player. Built on the shared project framework
(WiFi FSM, MQTT with NVS-persisted config, ElegantOTA + MQTT-pull OTA, task
watchdog, LED diagnostics, serial console). The speaker only plays on command —
it never auto-plays.

Sibling nodes built on the same framework: `../blackbox/` (door/mains/PIR +
relay beacon), `../../power/`, `../../vertical/`, `../../pir/`.

## Hardware

| Signal | ESP32 pin | Notes |
|---|---|---|
| JQ6500 RX | GPIO17 (UART2 TX) | ESP32 TX → module RX |
| JQ6500 TX | GPIO16 (UART2 RX) | module TX → ESP32 RX |
| JQ6500 GND / VCC | GND / 5V | 9600 baud, 8N1 |
| Diagnostic LED | GPIO2 | framework status blinks |

Audio tracks live on the JQ6500 **onboard flash**, addressed by index number
(`playFileByIndexNumber`). Valid range is `1..6` (`SPEAKER_TRACK_MAX` in
`config.h`). Playback is one-shot.

## Build

- Arduino IDE 2.x / `arduino-cli`, ESP32 Arduino core ≥ 3.0 (ESP-IDF 5.x),
  Board: *ESP32 Dev Module*.
- Libraries:
  - `JQ6500_Serial` (MP3 module)
  - `PubSubClient` (MQTT)
  - `ArduinoJson` v7
  - `ESPAsyncWebServer` + `AsyncTCP`
  - `ElegantOTA` v3

```bash
arduino-cli lib install JQ6500_Serial PubSubClient ArduinoJson ElegantOTA
arduino-cli compile --fqbn esp32:esp32:esp32 .
```

## Defaults

| Key | Default |
|---|---|
| WiFi SSID / pass | `TELKOMSELIOT` / _(set in config.h)_ |
| MQTT broker | `broker.emqx.io:1883` |
| Client ID | `esp32-speaker-<mac12-lowercase>` |
| Status-poll / snapshot interval | `1000 ms` poll, snapshot every `60 s` |
| Default volume (first boot) | `50%` (then persisted in NVS) |
| Heartbeat | `5 min` (fixed) |
| Watchdog | `60 s` (panic + reset) |
| Offline-restart | MQTT down for `10 min` ⇒ auto-restart |

All WiFi/MQTT defaults are overridable at runtime via `…/config` or the serial
console, and persist in NVS.

## MQTT topics

All scoped under `nms/<client_id>/speaker/`.

| Direction | Topic | Cadence |
|---|---|---|
| publish | `nms/<cid>/speaker/speaker` | on each command, on track-finished, + 60 s snapshot |
| subscribe | `nms/<cid>/speaker/config` | inbound commands (play/volume/stop + framework) |
| publish | `nms/<cid>/speaker/config/response` | command acks |
| publish | `nms/<cid>/speaker/heartbeat` | every 5 min |
| publish | `nms/<cid>/speaker/info` | once per MQTT connect (retained) |
| subscribe | `nms/<cid>/speaker/audit` | inbound audit |
| publish | `nms/<cid>/speaker/audit/response` | audit reply |
| publish | `nms/<cid>/speaker/ota/status` | OTA progress |

### Speaker commands (publish to `…/config`)

```jsonc
// Set volume to 70% (0..100), then play onboard track 3 (1..6)
{"speaker": {"play": 3, "volume": 70}}

// Play track 2 at the current/persisted volume
{"speaker": {"play": 2}}

// Set volume only (persisted to NVS, no playback change)
{"speaker": {"volume": 40}}

// Stop playback now
{"speaker": {"stop": true}}
```

Targeting is by `client_id` in the topic — no `device` field is needed.
`volume` is constrained to 0–100 % and mapped to the JQ6500's native 0–30.
A command is rejected (`failed` ack) if `play` is out of range or none of
`play` / `volume` / `stop` is present.

Acks are published to `…/config/response` as
`{ "config_speaker": { "status": "success" | "failed" } }`.

### Speaker state payload (`…/speaker`)

```json
{ "ip": "192.168.1.42", "ts": 12345678, "playing": true, "track": 3, "volume": 70 }
```

Published immediately after each accepted command, when a one-shot track
finishes (`playing` → `false`), once at boot, and on the 60 s snapshot.

### Framework config commands (publish to `…/config`)

```jsonc
{"wifi": {"ssid": "...", "pass": "..."}}                 // update WiFi, restart
{"mqtt": {"host": "...", "port": 1883, "user": "...",    // update broker, restart
          "pass": "...", "client_id": "..."}}
{"interval": {"delay_ms": 2000}}                          // status-poll cadence, restart
{"reset": {"action": true}}                               // soft restart
{"ota": {"url": "http://host/firmware.bin", "md5": "..."}}// HTTP firmware pull
{"factory_reset": {"action": true}}                       // wipe NVS, restart
```

### Audit commands (publish to `…/audit`)

```jsonc
{"last_config": {}}   // current config (passwords redacted) → …/audit/response
{"heartbeat": {}}     // IP + uptime + fw
{"info": {}}          // fw, project, build, mac, client_id
```

## Serial console (115200 8N1)

`STATUS`, `VERSION`, `HEARTBEAT`, `CONFIG`, `WIFI {...}`, `MQTT {...}`,
`INTERVAL {"delay_ms":N}`, `OTA {"url":...}`, `RESET`,
`FACTORY_RESET {"action":true}` — same framework console as the other nodes.

## LED indicator (`GPIO2`)

| Blinks | Meaning |
|---|---|
| 1× | Publish OK |
| 2× | MQTT publish / connect failed |
| 3× | WiFi connect failed |

## OTA

- **Web UI**: `http://<device-ip>/update` (ElegantOTA, no auth).
- **MQTT pull**: publish `{"ota": {"url": "http://host/firmware.bin"}}` to
  `…/config`. Progress mirrored to `…/ota/status`.

Both pause state publishes (`otaIsActive()`), and the device reboots on success.

## Reliability

- Non-blocking WiFi FSM, 60 s task watchdog (fed every loop).
- NVS-persisted config + volume survive power loss.
- 1 KB MQTT buffer, 30 s keepalive, 10 min offline-restart guard.

## Verification

```bash
# watch state + acks
mosquitto_sub -h broker.emqx.io -t 'nms/+/speaker/#' -v

# play track 1 at 60%
mosquitto_pub -h broker.emqx.io -t 'nms/<cid>/speaker/config' \
  -m '{"speaker":{"play":1,"volume":60}}'
```

Expect: audio plays, a `config/response` `success` ack, and a state message
`{"playing":true,"track":1,"volume":60}`; a `{"playing":false,...}` follows
when the track ends. Power-cycle and confirm the boot snapshot shows the
persisted volume. Sending `{"speaker":{"play":99}}` returns a `failed` ack
with no playback.
