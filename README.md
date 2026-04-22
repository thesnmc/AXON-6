# 🚀 AXON-6 Telemetry Engine
> A zero-latency, cryptographically secure UDP telemetry middleware for brain-computer interfaces and robotic kinematics.

---

## 📖 Overview
Modern Brain-Computer Interfaces (BCI) and robotic hardware require sub-millisecond reaction times to function safely and effectively. Standard network protocols (like TCP) introduce catastrophic kinematic stutter when waiting for dropped packets, while standard UDP streams are vulnerable to interception and total data loss during network volatility. AXON-6 bridges this gap by acting as a highly optimized, strictly unidirectional middleware pipeline.

By replacing standard transmission requests with dynamic Reed-Solomon Forward Error Correction (FEC), AXON-6 mathematically reconstructs shattered packets mid-air. It adapts its parity shielding in real-time based on network weather, ensuring the physical hardware never stalls.

Furthermore, AXON-6 is built on a foundation of absolute privacy. Every biological float-point array is sealed with ChaCha20-Poly1305 encryption before it ever hits the network card. It operates completely offline, allowing engineers to connect biological signals to physical servos without a single byte of data touching a corporate cloud server.

**The Core Mandate:** Absolute kinematic speed, dynamic mathematical resilience, and an uncompromising commitment to local data sovereignty.

## ✨ Key Features
* **Sub-Millisecond Latency:** Bypasses TCP handshakes entirely. Utilizes OS-level asynchronous `DatagramProtocol` queueing to ensure Python idles at 0% CPU until physical network interrupts occur.
* **Military-Grade Security:** Payloads are sealed using ChaCha20-Poly1305 encryption with unique 12-byte nonces, eliminating the possibility of interception, spoofing, or replay attacks.
* **Reed-Solomon Deep Healing:** Implements dynamic matrix math to execute Forward Error Correction (FEC). Rebuilds missing telemetry frames from parity packets without ever requesting a retransmission.
* **Decoupled 60FPS Diagnostic Visor:** A stateless HTML5/WebSocket frontend that visualizes raw network health and mathematically healed truth data, entirely independent of the core hardware pipeline.
* **Authenticated Kill Switch:** An un-spoofable, hardware-level operational abort feature that bypasses standard payloads, requiring a precise 32-byte secret key to execute.
* **Original-Payload Short-Circuiting:** An optimization engine that instantly bypasses heavy FEC matrix calculations if only parity packets are lost during a storm.

## 🛠️ Tech Stack
* **Language:** Python 3.14+ (Core Engine) / HTML5 & JavaScript (Visor UI)
* **Framework:** Python `asyncio` for non-blocking, OS-level concurrency.
* **Environment:** VS Code / Linux Edge Devices (Raspberry Pi / ESP32 integration)
* **Key Libraries/APIs:** `cryptography` (ChaCha20 C-extensions), `reedsolo` (Error Correction), `websockets` (UI relay), `edfio` (Clinical data parsing).

## ⚙️ Architecture & Data Flow
The system is cleanly divided into three distinct operational nodes:

* **Input (The Emitter):** Biological data (64-bit float arrays) is ingested, dynamically sized into blocks, shielded with Reed-Solomon parity matrices, encrypted, and blasted over the UDP socket.
* **Processing (The Receiver):** The edge node captures the packet, verifies the Poly1305 MAC tag, decrypts the payload, and feeds it into the erasure matrix for structural healing. Dead blocks are purged asynchronously.
* **Output (The Bridge & Visor):** The healed, pristine float array is split. One stream is relayed via WebSockets to the diagnostic UI, while the primary stream is mapped to kinematics and pushed via Serial/I2C to the physical servomotors.

## 🔒 Privacy & Data Sovereignty
* **Data Collection:** Absolute zero. Telemetry is transmitted point-to-point and vanishes the moment the kinematic frame is executed.
* **Permissions Required:** Standard local network binding for UDP/WebSocket protocols. No external permissions are requested or utilized.
* **Cloud Connectivity:** Strictly disabled by design. AXON-6 relies entirely on local area networks (LAN) or direct point-to-point interfaces, ensuring Sovereign control over biological data.

## 🚀 Getting Started

### Prerequisites
* **Minimum OS:** Windows 10/11, Linux, or macOS.
* **Python:** 3.10 or higher.
* **Required development environment:** VS Code or any standard Python IDE.

### Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/thesnmc/AXON-6.git](https://github.com/thesnmc/AXON-6.git)
   ```

2. Open the project in your IDE and navigate to the project root.

3. **Install the required cryptographic and mathematical dependencies:**
   ```bash
   pip install cryptography reedsolo websockets edfio
   ```

4. Boot the 60FPS Diagnostic Visor by opening `examples/visor.html` in your web browser.

5. **Launch the Receiver node in Terminal 1:**
   ```bash
   python -m examples.demo_receiver
   ```

6. **Fire the Emitter sequence in Terminal 2 to commence the encrypted stream:**
   ```bash
   python examples/legacy_emitter.py
   ```

## 🤝 Contributing
Contributions, issues, and feature requests are welcome. Feel free to check the issues page if you want to contribute to the telemetry protocol, resilience math, or hardware bridge implementations.

## 📄 License
This project is licensed under the TheSNMC License - see the LICENSE file for details.  
Built by an independent developer in Chennai, India.