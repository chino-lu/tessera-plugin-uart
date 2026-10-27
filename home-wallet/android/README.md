# Home Wallet — Android app

The wallet app: your passes as cards (with a rotating QR code), one-tap door
opening, the access log, and NFC host card emulation so the phone itself is
the tag a door reader scans.

## Build

Requirements: JDK 17 and Android Studio (or just the command line with the
Android SDK installed).

```bash
cd android
./gradlew assembleDebug      # app/build/outputs/apk/debug/app-debug.apk
./gradlew assembleRelease    # signed release build (configure signing first)
```

The debug APK installs with `adb install app/build/outputs/apk/debug/app-debug.apk`.

## Set up

1. Install the **Home Wallet** integration in Home Assistant (see the parent README).
2. In Home Assistant, create a **long-lived access token** (your profile → *Long-Lived Access Tokens*).
3. Open the app → **Settings** tab → enter your HA URL (e.g. `https://home.example.com`) and the token → **Save**.
4. Your wallets appear on the **Wallet** tab.

## Use

- **Wallet tab** — one card per pass. Hold a card (or tap it) to show the QR code. The code refreshes every 30 seconds; a screenshot of it expires quickly.
- **NFC** — with *NFC pass* enabled in Settings, hold the phone (screen on or off) to a reader that selects AID `F0394148148100`; the phone answers with the current token. Home Assistant verifies it and opens the door.
- **Doors tab** — open any door with a tap, no code needed.
- **Log tab** — the last access attempts, granted and denied.

## How it talks to Home Assistant

- `GET /api/home_wallet/token?wallet_id=..&door_id=..` (REST) — the current rotating token for the QR code, refreshed every 15 s.
- Websocket `/api/websocket` — `home_wallet/wallets`, `home_wallet/doors`, `home_wallet/history`, `home_wallet/open_door`, authenticated with the long-lived access token.

All state (URL, token) is stored in Android DataStore on the device; the token is only ever sent to your Home Assistant server.
