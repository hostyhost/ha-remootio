# Remootio for Home Assistant

A self-contained [Home Assistant](https://www.home-assistant.io/) custom
integration for [Remootio](https://www.remootio.com/) smart garage door and
gate controllers. It exposes your Remootio device as a `cover` entity that you
can open and close, and that reports its open/closed state in real time over
Remootio's local WebSocket API (`local_push`).

## What "self-contained" means

This integration is a fork that **vendors** its WebSocket client
(`aioremootio`) directly inside the integration and depends on **nothing
outside of what Home Assistant already ships**. The integration's
`manifest.json` declares an empty `"requirements": []`:

- AES-256-CBC encryption and HMAC-SHA256 authentication of the Remootio
  protocol are implemented with the
  [`cryptography`](https://cryptography.io/) library and the Python standard
  library (`hmac`, `hashlib`, `os.urandom`) — no `pycryptodome`.
- No `async-class` dependency and no `git+https` requirement pulling code from
  a third-party repository at install time.

Because there is nothing to download from PyPI or GitHub at runtime, the
integration installs cleanly via HACS and works in restricted/offline
environments.

## Features

- `cover` entity supporting **open** and **close**.
- Live state updates (open / closed / opening / closing) via local push.
- Device information (model, serial number, API version) in the device
  registry.
- A `remootio_left_open` Home Assistant event fired when the device reports the
  door/gate was left open.
- A **reauthentication** flow: if the API keys change, Home Assistant prompts
  you to enter the new keys for the same device.

## Requirements

- Home Assistant **2024.6.0** or newer.
- A Remootio device that is:
  - connected to your Wi-Fi with a fixed IP address (or a resolvable host
    name),
  - fitted with the status **sensor** (so open/closed can be detected),
  - running software new enough to expose the **WebSocket API** (enable it in
    the Remootio app under _Device software → Websocket API_, with logging
    enabled).

When you enable the API, the Remootio app shows the device's IP address, the
**API Secret Key** and the **API Auth Key** — you need all three to set up the
integration.

## Installation

### Via HACS (recommended)

1. In HACS, add this repository as a **custom repository** of type
   _Integration_.
2. Install **Remootio** from HACS.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for
   **Remootio**.

### Manual

1. Copy the `custom_components/remootio` directory into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & Services**.

## Configuration

The integration is configured entirely from the UI. You will be asked for:

| Field | Description |
| --- | --- |
| Host | IP address or host name of your Remootio device |
| API Secret Key | 64-character key shown by the Remootio app |
| API Auth Key | 64-character key shown by the Remootio app |
| Controlled device's class | `garage` or `gate` |

## Credits and license

This integration is a modernized, self-contained fork of the original work:

- Home Assistant integration: **ivgg-me** /
  [`sam43434/remootio`](https://github.com/sam43434/remootio)
- WebSocket client library: **Gergő Gábor Ilyés-Veisz** /
  [`sam43434/aioremootio`](https://github.com/sam43434/aioremootio)

The vendored `aioremootio` client retains its original Apache License 2.0
headers, and a copy of the license is included at
`custom_components/remootio/aioremootio/LICENSE`. This repository is
distributed under the Apache License 2.0.

"Remootio" is a trademark of Assemblabs Ltd. This project is not affiliated
with or endorsed by Assemblabs Ltd.
