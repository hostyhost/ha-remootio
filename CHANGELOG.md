# Changelog

All notable changes to this project are documented in this file.

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
