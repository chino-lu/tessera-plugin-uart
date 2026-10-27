# Home Wallet

Manage access at home from Home Assistant, with a wallet app on your phone. A bit like UniFi Access, but built on Home Assistant: passes live in HA, the phone is the pass, and every door, grant and denial is logged in one place.

```
┌────────────────────┐      rotating QR / NFC token       ┌─────────────────────┐
│  Home Wallet app   │ ─────────────────────────────────► │  door reader (QR /  │
│  (Android, APK)    │                                    │  NFC scanner, ESPHome)│
└────────────────────┘                                    └──────────┬──────────┘
         ▲                                                            │ token
         │  websocket + REST (long-lived access token)                 ▼
┌────────┴───────────┐        home_wallet/check_token          ┌────────────┐
│  Home Assistant    │ ◄────────────────────────────────────── │  your lock │
│  home_wallet       │ ──► lock.open / cover.open ───────────► │  / cover   │
│  (custom component)│                                         └────────────┘
└────────────────────┘
```

## What it does

- **Wallets (passes).** One wallet per person. A wallet is a person entity, a secret, and optionally a PIN. The app shows it as a card; hold the card to reveal a QR code.
- **Rotating tokens.** The QR code and the NFC tag carry an HMAC-SHA256-signed token bound to one wallet and one door, valid for 30 seconds. Screenshots and skimmed codes expire on their own. Rotate or delete a wallet and every old code stops working immediately.
- **Doors.** Register any `lock`, `cover` or `switch` entity as a door. The app opens it with a tap; a `button` entity per door appears in HA too.
- **PIN.** Optional per-wallet PIN (PBKDF2-hashed) for keypads.
- **Access log.** Every attempt — granted or denied, by QR, NFC, PIN, button or app — is stored (last 500) and fired as a `home_wallet_access` event, so you can automate on it.
- **NFC.** The phone itself is the NFC tag (host card emulation): hold it to a reader and it answers with the current token.

## Install the Home Assistant side

Via HACS (add this repository as a custom repository, category *Integration*), or copy `custom_components/home_wallet` into your `config/custom_components/` and restart.

Then **Settings → Devices & Services → Add Integration → Home Wallet**. The config flow asks for your HA URL and a long-lived access token (create one under your profile → *Long-Lived Access Tokens*).

Optionally pre-configure doors and people in `configuration.yaml`:

```yaml
home_wallet:
  pin_length: 6
  people:
    - person.sam
  doors:
    - name: Front door
      entity_id: lock.front_door
    - name: Gate
      entity_id: cover.gate
```

## Manage access

Everything is also available as services, so you can drive it from automations, dashboards or Node-RED:

| Service | What it does |
|---|---|
| `home_wallet.create_wallet` | Create a pass for a person (`name`, optional `user_id`, `person`) |
| `home_wallet.delete_wallet` | Delete a pass (its codes stop working immediately) |
| `home_wallet.rotate_wallet` | New secret; old codes stop working (the app picks up the new code by itself) |
| `home_wallet.revoke_wallet` | Deactivate a pass, keep its history |
| `home_wallet.set_pin` | Set (or clear) a wallet's PIN |
| `home_wallet.add_door` / `home_wallet.remove_door` | Register / remove a door |
| `home_wallet.open_door` | Open a door |

Each wallet also gets a `sensor.<name>_pass` (state `active`/`revoked`, attributes with grant/denial counts) and each door an `button.open_<door>`.

### Let a reader open a door

A QR scanner or NFC reader (for example an ESP32 running ESPHome, or one of your Tessera screens) submits what it scanned over the websocket API:

```json
{"id": 1, "type": "home_wallet/check_token", "code": "<scanned token>", "door_id": "1a2b3c4d"}
{"id": 2, "type": "home_wallet/check_pin", "code": "483920", "door_id": "1a2b3c4d"}
```

Both verify and open the door, and return `granted` plus a `reason`. The websocket commands `home_wallet/wallets`, `home_wallet/doors`, `home_wallet/history`, `home_wallet/wallet_token`, `home_wallet/create_wallet`, `home_wallet/delete_wallet`, `home_wallet/rotate_wallet` and `home_wallet/open_door` are what the app itself uses.

## The Android app

The wallet APK is in [`android/`](android). See [android/README.md](android/README.md) for building it. In short:

1. Install the integration and create a long-lived access token in HA.
2. Build the APK (`./gradlew assembleDebug`) or sideload the release build.
3. Open the app → Settings, enter your HA URL and the token.
4. Your passes appear as cards. Hold a card for the QR code, hold the phone to an NFC reader, or use the Doors tab.

## Layout

```
home-wallet/
├── custom_components/home_wallet/   # the Home Assistant integration
│   ├── tokens.py                    # HMAC tokens, PIN hashing (stdlib only)
│   ├── manager.py                   # wallets, doors, access decisions, history
│   ├── websocket_api.py             # the commands the app and readers use
│   ├── button.py / sensor.py        # door buttons and pass sensors
│   └── services.yaml                # the services above
├── android/                         # the wallet app (Kotlin, Jetpack Compose)
└── tests/                           # python3 -m unittest discover tests
```

## Tests

The token, PIN and access-decision logic is covered by unit tests that run without Home Assistant:

```bash
cd home-wallet
python3 -m unittest discover tests
```

## Security notes

- The wallet secret never leaves Home Assistant; the app only ever receives the short-lived signed token.
- Tokens are bound to a single door and expire after 30 seconds (one window of clock-skew tolerance).
- PINs are stored as salted PBKDF2-HMAC-SHA256 hashes, never in plain text.
- The app talks to HA over your normal HTTPS connection with a long-lived access token; revoke the token in HA if a phone is lost, then rotate the wallets on that phone.
