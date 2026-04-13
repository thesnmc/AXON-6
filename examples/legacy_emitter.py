# AXON-6 Telemetry Engine (SECURE TIMELINE - CHACHA20)
# Copyright 2026 thesnmc
import struct
import socket
import asyncio
import random
import time
import os
import json
import websockets
import edfio
from reedsolo import RSCodec
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

class FeedbackProtocol(asyncio.DatagramProtocol):
    def __init__(self, emitter):
        self.emitter = emitter

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            new_parity = int(data.decode().strip())
            if new_parity != self.emitter.current_parity:
                self.emitter.current_parity = new_parity
                self.emitter.rs = RSCodec(self.emitter.current_parity * 8)
                print(f"🔄 SHIELDS ADAPTED: Matrix shifted to {self.emitter.current_parity} Parity Packets.")
        except ValueError:
            print(f"⚠️ [SECURITY] Dropped malformed feedback packet from {addr[0]}")

class AxonEmitter:
    def __init__(self, target_ip="127.0.0.1", data_port=5005, feedback_port=5006, simulate_weather=False):
        self.UDP_IP = target_ip
        self.DATA_PORT = data_port
        self.FEEDBACK_PORT = feedback_port
        
        self.SECRET_KEY = b"AXON-PRO-KEY" 
        
        # 🛡️ V3.3 SECURE CORE: 32-Byte Master Encryption Key
        self.ENCRYPTION_KEY = b"AXON-6-MILITARY-GRADE-KEY-32BYTE"
        self.chacha = ChaCha20Poly1305(self.ENCRYPTION_KEY)
        
        self.PACKET_FORMAT = '>B I I H B B d' 
        self.current_parity = 1
        self.rs = RSCodec(self.current_parity * 8) 
        
        self.simulate_weather = simulate_weather
        self.network_weather = 0.0
        
        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.visor_ws = None
        self.block_id = 1

    async def connect_visor(self, uri="ws://127.0.0.1:8765"):
        try:
            self.visor_ws = await websockets.connect(uri)
            print("🔗 [AXON-6] Uplink established with Visor Dashboard.")
        except Exception:
            print("⚠️ [AXON-6] Visor Dashboard offline. Running blind.")

    async def listen_for_feedback(self):
        loop = asyncio.get_running_loop()
        try:
            await loop.create_datagram_endpoint(
                lambda: FeedbackProtocol(self),
                local_addr=("0.0.0.0", self.FEEDBACK_PORT)
            )
        except Exception as e:
            print(f"❌ [BIND ERROR] Feedback port: {e}")
        while True:
            await asyncio.sleep(3600)

    async def weather_loop(self):
        while self.simulate_weather:
            await asyncio.sleep(6)
            weather_states = [0.0, 0.15, 0.40]
            self.network_weather = random.choice(weather_states)
            w_name = "☀️ CLEAR" if self.network_weather == 0 else ("🌧️ CLOUDY" if self.network_weather < 0.2 else "⛈️ STORM")
            print(f"\n[WEATHER] {w_name} WARNING: {int(self.network_weather*100)}% Packet Loss\n")

    async def transmit(self, data_chunk):
        payload_size = len(data_chunk)
        data_bytes = bytearray()
        for value in data_chunk:
            data_bytes.extend(struct.pack('>d', float(value)))
            
        encoded_block = self.rs.encode(data_bytes)
        total_packets = payload_size + self.current_parity
        birth_time = time.time()
        
        packets = []
        for seq in range(total_packets):
            chunk = encoded_block[seq*8 : (seq+1)*8]
            
            # 🛡️ V3.3 SECURE CORE: ENCRYPTION
            nonce = os.urandom(12)
            encrypted_chunk = self.chacha.encrypt(nonce, chunk, None)
            secure_payload = nonce + encrypted_chunk
            
            p_type = 0 if seq < payload_size else 1
            header = struct.pack(self.PACKET_FORMAT, p_type, self.block_id, seq, len(secure_payload), self.current_parity, payload_size, birth_time)
            packets.append(header + secure_payload)

        if self.visor_ws:
            try:
                await self.visor_ws.send(json.dumps({
                    "type": "original_brainwave",
                    "data": data_chunk
                }))
            except websockets.exceptions.ConnectionClosed:
                self.visor_ws = None 

        destroyed = []
        for seq, packet in enumerate(packets):
            if random.random() > self.network_weather:
                self.sock_out.sendto(packet, (self.UDP_IP, self.DATA_PORT))
            else:
                destroyed.append(seq)
        
        if destroyed:
            print(f"🔥 BLOCK {self.block_id}: Weather destroyed packets {destroyed}!")
        else:
            print(f"✅ BLOCK {self.block_id}: Perfect transmission.")
            
        self.block_id += 1

    def send_poison_pill(self):
        print("💊 Sending Authenticated Poison Pill to Receiver...")
        header = struct.pack(self.PACKET_FORMAT, 9, 0, 0, len(self.SECRET_KEY), 0, 0, time.time())
        packet = header + self.SECRET_KEY
        self.sock_out.sendto(packet, (self.UDP_IP, self.DATA_PORT))
        print("🔌 Emitter shutting down gracefully.")


async def main():
    print("🧠 Booting AXON-6 Secure Emitter...")
    emitter = AxonEmitter(simulate_weather=True)
    await emitter.connect_visor()

    # Load clinical EEG data
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        edf_path = os.path.join(current_dir, "brainwave_sample.edf")
        edf = edfio.read_edf(edf_path)
        brain_signal = edf.signals[0].data
        print("🚀 Clinical data loaded. Commencing encrypted transmission...")
    except FileNotFoundError:
        print("⚠️ EDF file not found. Generating secure synthetic brainwaves...")
        brain_signal = [random.uniform(-100, 100) for _ in range(1000)]

    # Start background tasks
    loop = asyncio.get_running_loop()
    loop.create_task(emitter.listen_for_feedback())
    loop.create_task(emitter.weather_loop())

    # Main transmission loop
    for i in range(0, len(brain_signal) - 5, 5):
        chunk = brain_signal[i:i+5]
        if len(chunk) == 5:
            # Convert numpy array elements to floats so JSON serialization doesn't crash
            float_chunk = [float(x) for x in chunk]
            await emitter.transmit(float_chunk)
        await asyncio.sleep(0.1) # Accelerated to 10 FPS

    emitter.send_poison_pill()

if __name__ == "__main__":
    asyncio.run(main())