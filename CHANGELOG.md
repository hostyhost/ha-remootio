# Changelog

All notable changes to this project are documented in this file.

## v2.1.0

Expose everything the Remootio Websocket API offers as Home Assistant entities.

### Added

New `sensor`, `binary_sensor`, and `button` platforms built from the device's
event stream and the existing `cover`:

- **Sensors:** *Last operated by* (key + connection method, with `via` /
  `key_type` / `key_number` attributes), *Last event*, *Uptime* (diagnostic),
  and *Left open duration*.
- **Binary sensors:** *Connectivity* (diagnostic, stays available while
  disconnected), *Left open* (problem), *Status sensor enabled*, *Manual button
  enabled*, *Doorbell enabled*, and *Relay output 1/2 active* (diagnostic).
- **Buttons:** *Trigger* (pulses the control output regardless of the known
  state — useful when the door state is uncertain), *Trigger secondary output*
  (for devices with a free relay), and *Restart device*.
- The `cover` now carries `serial_number`, `api_version`, and `uptime`
  attributes, and the device **model** is now reported correctly (including
  Remootio 3) instead of showing "unknown".
- Device events are forwarded onto the Home Assistant event bus as
  `remootio_relay_trigger`, `remootio_doorbell_pushed`,
  `remootio_manual_button_pushed`, `remootio_key_management`,
  `remootio_sensor_flipped`, `remootio_restart`, and more, for use as
  automation triggers (`remootio_left_open` is unchanged).

### Changed

- The vendored `aioremootio` client now parses the full v3 event set
  (secondary relay, key connected, key management, manual button, doorbell,
  sensor enable/flip/disable, and relay-output activation events) and exposes
  the derived telemetry via new client properties and an update-listener
  callback. Replayed history on reconnect initializes the status sensors
  without re-firing automation events.

### Notes

- The Remootio Websocket API is control/telemetry only — it cannot **write**
  device settings, so items like sensor logic, auto-open, and key management
  are exposed as **read-only** sensors, not switches. Wi-Fi signal, sensor
  battery, and firmware version are not exposed by the API and therefore are
  not available.
- Event-driven status entities populate once the device sends the relevant
  event; they require the device's **API logging** to be enabled.

## v2.0.6

Stop the recurring `AUTHENTICATION_ERROR` / reconnect churn around door operations.

### Fixed

- Action requests sent to the device are now serialized through a single lock
  that is held across id allocation, encryption, and the actual websocket send.
  Previously a background state poll could overlap a user- or automation-initiated
  `OPEN`/`CLOSE` and place a frame on the wire out of action-id order. Remootio
  closes the session with an `AUTHENTICATION_ERROR` whenever it receives an action
  id that isn't exactly the previous id incremented by one, which dropped the
  connection (briefly flipping the cover to `unavailable`) and lost the door's
  in-progress state every time the gate was operated. The initial authentication
  `QUERY` shares the same lock.

### Changed

- The cover's backstop poll interval was relaxed from **30s to 90s**. The client
  already sends a `PING` keepalive every 60s (within Remootio's recommended
  60–90s window), so the periodic `QUERY` only needs to recover an occasionally
  missed push event. The longer interval cuts action-id traffic and the window in
  which a poll can collide with a real door operation, while a missed state push
  still self-corrects within the interval.

## v2.0.5

Smoother recovery when the device rejects authentication.

### Fixed

- `ErrorType.AUTHENTICATION_ERROR` from the device is now handled explicitly:
  the client forces a clean disconnect (clearing the session key and per-session
  state) so the self-healing loop reconnects with a fresh authentication
  sequence, instead of just logging the error and leaving the half-authenticated
  state in place. Helps when the device's session state gets wedged after rapid
  drop/reconnect cycles on a flaky link.
- Replaced a duplicate `AUTHENTICATION_TIMEOUT` branch (dead code from the
  upstream) with the new `AUTHENTICATION_ERROR` branch.

## v2.0.4

Quieter, cleaner behavior while disconnected.

### Fixed

- Sending an action (state poll, open, or close) while the device is unreachable
  no longer raises a `TypeError` (`__last_action_id` was `None`). `__trigger` now
  raises a clear `RemootioClientConnectionEstablishmentError` when no connection
  can be established.
- The cover's periodic poll now only queries the device when connected;
  reconnection is left to the client's self-healing loop, so polls during an
  outage are a quiet no-op instead of logging an error every interval.

## v2.0.3

Keep cover state in sync with the device.

### Fixed

- The cover could get stuck on a stale state (e.g. showing `opening`/`open`
  while the door was actually closed) when the device dropped its websocket
  around an operation and never re-pushed the follow-up state-change event.
  The entity now polls the device periodically (every 30s) as a backstop, so a
  missed push event self-corrects within the interval. Pushed events still
  update state instantly; the periodic query also acts as a keepalive and
  reconnect trigger.

## v2.0.2

Self-healing reconnection.

### Fixed

- The background message-receiver and ping-sender loops no longer terminate
  permanently on an unexpected error (e.g. a websocket read raising on a
  connection reset/timeout). Both loops now treat any non-cancellation error or
  disconnect as transient: they log, wait briefly, and reconnect — so the client
  recovers on its own from dropped connections without needing a config-entry
  reload or a Home Assistant restart. The loops still stop cleanly when the
  client is terminated (`CancelledError` is always re-raised).
- A `WSMsgType.ERROR` websocket frame is now treated as a closed connection and
  triggers reconnection.

## v2.0.1

Bug fixes for connection-failure handling.

### Fixed

- A device that is unreachable now fails with a clear **"Cannot connect"** within
  a few seconds instead of hanging ~60 seconds and reporting **"Unknown error."**
  `ws_connect` now uses a 10-second connect timeout.
- `__initialize` no longer swallows `asyncio.CancelledError` (it is re-raised
  rather than wrapped), so setup timeouts surface as `TimeoutError` /
  `ConfigEntryNotReady` and Home Assistant's task cancellation and shutdown work
  correctly.

## v2.0.0

First release of the **self-contained** fork of the Remootio integration for
Home Assistant — installable via HACS with **zero external dependencies**.

### Highlights

- **Self-contained, no external dependencies.** The `aioremootio` WebSocket
  client is vendored inside the integration and `manifest.json` declares an
  empty `"requirements": []`. Nothing is fetched from PyPI or GitHub at install
  time, so it works in restricted/offline environments.
- **Modernized cryptography.** AES-256-CBC and HMAC-SHA256 are now implemented
  with the [`cryptography`](https://cryptography.io/) library and the Python
  standard library (`hmac`, `hashlib`, `os.urandom`) instead of
  `pycryptodome`. The wire protocol is byte-for-byte identical; MAC
  verification uses `hmac.compare_digest`.
- **Reauthentication flow.** If the device's API keys change, Home Assistant
  prompts you to re-enter them. Credentials are validated against the *same*
  device — entering keys for a different device is rejected.

### Added

- Reauth flow (`reauth` / `reauth_confirm`) with a `wrong_device` safeguard.
- Device registry info: manufacturer (Assemblabs Ltd), model (from the
  device type), serial number, and API version.
- `remootio_left_open` Home Assistant event when the device reports it was
  left open.

### Changed

- Removed the `async-class` dependency: the client is now a plain class with a
  `RemootioClient.create(...)` classmethod and an internal task store.
- Connection failures surface promptly instead of hanging (~60s before).
- The integration stores its client in `entry.runtime_data` and maps errors to
  `ConfigEntryAuthFailed` / `ConfigEntryNotReady`.
- Config flow uses the modern `ConfigFlow` / `ConfigFlowResult` APIs and never
  logs secrets.
- `manifest.json` version bumped to `2.0.0`, `integration_type: device`,
  `iot_class: local_push`, empty `requirements`.

### Requirements

- Home Assistant **2024.6.0** or newer.
- A Remootio device on Wi-Fi with a fixed IP/host name, a status sensor
  installed, and the WebSocket API enabled.

### Installation

Install via HACS (add as a custom repository of type *Integration*) or copy
`custom_components/remootio` into your `config/custom_components/` directory,
then restart Home Assistant and add the integration from
**Settings → Devices & Services**.

### Credits

A modernized, self-contained fork of the original work by **ivgg-me** /
[`sam43434/remootio`](https://github.com/sam43434/remootio) and
**Gergő Gábor Ilyés-Veisz** /
[`sam43434/aioremootio`](https://github.com/sam43434/aioremootio). The vendored
client retains its Apache License 2.0 headers; distributed under Apache 2.0.

"Remootio" is a trademark of Assemblabs Ltd. This project is not affiliated
with or endorsed by Assemblabs Ltd.
