# 🏗️ Architecture & Design Document: AXON-6 Telemetry Engine
**Version:** 3.3.0 Secure Core | **Date:** 2026-04-22 | **Author:** Sujay

---

## 1. Executive Summary
This document outlines the architecture for AXON-6, a zero-latency, cryptographically secure UDP telemetry engine designed for high-speed brain-computer interface (BCI) to hardware communication. It acts as the secure middleware translating biological float-point arrays into physical kinematic commands for robotic hardware. The system operates entirely offline on local networks, utilizing dynamic Forward Error Correction (FEC) and military-grade encryption while strictly adhering to a data sovereignty mandate.

## 2. Architectural Drivers
*What forces shaped this architecture?*

* **Primary Goals:** Absolute kinematic speed (sub-millisecond latency), mathematical resilience to packet loss without retransmission requests, and complete data sovereignty.
* **Technical Constraints:** Must run natively in offline/air-gapped LAN environments without cloud dependencies. Must scale dynamically to handle payloads ranging from 5 floats (robotic hand) to 50 floats (full exoskeleton) dynamically.
* **Non-Functional Requirements (NFRs):** * **Security/Privacy:** All telemetry must be cryptographically sealed before network transmission; memory must be actively garbage-collected to prevent buffer leaks.
    * **Reliability:** Must function accurately in highly volatile network environments (up to 40% packet loss) using algorithmic reconstruction.
    * **Performance:** Python runtime must idle at 0% CPU until physical network interrupts occur, utilizing OS-level asynchronous queueing to prevent thread blocking.

## 3. System Architecture (The 10,000-Foot View)
The architecture is strictly decoupled into three primary nodes to ensure the failure of a diagnostic tool never interrupts the physical hardware link.

* **Presentation Layer (Visor):** A stateless, decoupled diagnostic HUD built with HTML5 Canvas and Chart.js. It connects to the Receiver via `127.0.0.1` WebSockets to plot network health versus mathematically healed truth data at 60FPS. 
* **Domain Layer (AXON Core):** The high-speed mathematical engine. Houses the asynchronous event queues, the ChaCha20-Poly1305 encryption/decryption routines, and the Reed-Solomon erasure matrix for Deep Healing.
* **Data/Hardware Layer (Bridge):** Direct interfaces with device networking (UDP DatagramSockets). Outputs healed float arrays to a pending hardware bridge utilizing USB Serial or I2C to interface directly with physical servomotors (Arduino/ESP32).

## 4. Design Decisions & Trade-Offs (The "Why")

* **Decision 1: Choosing UDP over TCP**
    * *Rationale:* TCP retransmission protocols introduce severe, unpredictable kinematic stutter when waiting for dropped packets to be resent.
    * *Trade-off:* Forces the implementation of complex, CPU-intensive Reed-Solomon Forward Error Correction (FEC) to recreate missing data mathematically, but guarantees real-time servo actuation without stutter.
* **Decision 2: The Decrypt-Then-Heal Pipeline**
    * *Rationale:* Security and CPU conservation.
    * *Trade-off:* Requires decrypting individual packet chunks before reassembly. However, tampered packets fail the MAC tag check instantly and are dropped, saving massive computational overhead by bypassing the Reed-Solomon healing algorithm entirely for hostile data.
* **Decision 3: AGPLv3 Licensing Model**
    * *Rationale:* Enforcing strict data sovereignty for the Atmanirbhar Bharat initiative. 
    * *Trade-off:* Introduces friction for corporations wanting to use the protocol in closed-source SaaS clouds, but legally forces any network/cloud modifications to be shared back with the open-source community, preventing proprietary hijacking.

## 5. Data Flow & Lifecycle
1. **Ingestion:** Clinical EEG or BCI data is ingested as raw 64-bit float arrays.
2. **Matrix Encoding:** The Emitter calculates dynamic payload size, generates the Reed-Solomon parity matrix based on current network weather, and chunks the data.
3. **Cryptographic Seal:** Each chunk is assigned a unique 12-byte Nonce and encrypted using ChaCha20-Poly1305.
4. **Transmission:** The encrypted binary payload (`>B I I H B B d`) is blasted over the UDP socket.
5. **Capture & Authentication:** The Receiver's OS-level asynchronous queue catches the packet. The Poly1305 MAC tag is verified. If tampered, the packet is immediately dropped.
6. **Decryption & Healing:** Valid packets are decrypted. If sequences are missing, surviving packets are injected into an erasure matrix where Reed-Solomon algorithms solve for the missing vectors.
7. **Execution/Output:** The healed 64-bit float array is simultaneously broadcast to the local WebSocket Visor and relayed to the physical Serial/I2C hardware bridge. Memory buffers are purged by the garbage collector after 2.0 seconds.

## 6. Security & Privacy Threat Model
* **Data at Rest:** Nothing is stored. Operations are completely stateless and exist only in volatile RAM for the duration of the packet lifecycle.
* **Data in Transit:** Secured via ChaCha20-Poly1305. A 32-byte symmetric master key is required for both the Emitter and Receiver.
* **Mitigated Risks:** * *Replay Attacks:* Prevented via strict, unique 12-byte Nonce validation per packet.
    * *Unauthorized Shutdowns:* Prevented via the Authenticated Kill Switch (`p_type = 9`), which bypasses standard payloads and requires a perfect 32-byte key match to execute a hardware abort.
    * *Corporate Interception:* Prevented by zero cloud connectivity. The system is designed to be air-gapped on a local LAN or point-to-point interface.

## 7. Future Architecture Roadmap
* **Hardware Bridge Implementation:** Development of the `RobotController.py` module to handle kinematic float-to-angle translations and baud-rate management for physical serial transmission to ESP32/Arduino targets.
* **Signal Decimation:** Implementing moving average filters within the `on_data_received` callback to safely down-sample 1000 FPS BCI data to match physical servo actuation limits (e.g., 50 FPS) without buffer overflow.
* **C++ Receiver Port:** Transitioning the Python receiver node to raw C++ or Rust for deployment on deeply embedded, low-RAM microcontrollers, bypassing the Python runtime overhead entirely.
