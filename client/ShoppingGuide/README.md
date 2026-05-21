# ShoppingGuide iOS Client Archive

SwiftUI MVP reference for the RAG ecommerce shopping guide. This is no longer the competition delivery path because the active development machine is Windows and the competition accepts either iOS or Android native apps.

The formal client is now `client-android` using Kotlin + Jetpack Compose.

## Run

1. Start the backend from `server`:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
2. Open `ShoppingGuide.xcodeproj` on macOS with Xcode 15 or newer.
3. Run the `ShoppingGuide` scheme on an iOS 17 simulator.

The app expects the backend at `http://127.0.0.1:8000`.
