# Android Client

Native Android client for the RAG ecommerce shopping guide.

## Stack

- Kotlin
- Jetpack Compose + Material 3
- ViewModel + StateFlow
- OkHttp streaming for SSE
- Kotlinx Serialization
- Coil for product images
- Source-marked answer blocks and structured comparison cards

## Run

1. Start the backend from the repository root:
   ```powershell
   cd server
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
2. Open `client-android` in Android Studio.
3. Run the `app` configuration on an emulator.

The app defaults to `http://10.0.2.2:8000`, which is the emulator route to the Windows host.

For a physical Android device:

1. Keep the backend bound to all interfaces with `--host 0.0.0.0`.
2. Make sure the phone and Windows machine are on the same network.
3. In the app's `服务地址` field, enter `http://<Windows WLAN IPv4>:8000` and tap `应用`.
4. If the app cannot load products, allow inbound TCP 8000 through Windows Firewall.

On this machine, the current WLAN IPv4 observed during setup was `172.24.7.60`, so the physical-device address would be `http://172.24.7.60:8000` while that network assignment remains unchanged.

## Tests

Core parser tests are in the `core` module:

```powershell
gradlew.bat :core:test
```

If Gradle test discovery fails under the current Chinese path, use the manual JUnit command documented in the root README or run the tests from Android Studio.
