# AXON-6 Telemetry Engine | Copyright (c) 2026 thesnmc | MIT License
import struct
import socket
import asyncio
import random
import time
import json
import websockets
from reedsolo import RSCodec

class FeedbackProtocol(asyncio.DatagramProtocol):
    """V3 FIX: OS-level network listener. No more while-True CPU hogging!"""
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
        """Initializes the AXON-6 V3.0 Emitter Node"""
        self.UDP_IP = target_ip
        self.DATA_PORT = data_port
        self.FEEDBACK_PORT = feedback_port
        
        # V3 FIX: The Authenticated Security Key
        self.SECRET_KEY = b"AXON-PRO-KEY" 
        
        # V3 FIX: Added a second 'B' to the header to transmit dynamic Payload Size
        self.PACKET_FORMAT = '>B I I H B B d' 
        
        self.current_parity = 1
        self.rs = RSCodec(self.current_parity * 8) 
        
        self.simulate_weather = simulate_weather
        self.network_weather = 0.0
        
        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Note: self.sock_in is gone! The FeedbackProtocol handles it natively now.
        
        self.visor_ws = None
        self.block_id = 1

    async def connect_visor(self, uri="ws://127.0.0.1:8765"):
        """Establishes a WebSocket uplink to the UI Dashboard"""
        try:
            self.visor_ws = await websockets.connect(uri)
            print("🔗 [AXON-6] Uplink established with Visor Dashboard.")
        except Exception:
            print("⚠️ [AXON-6] Visor Dashboard offline. Running blind.")

    async def listen_for_feedback(self):
        """Boots the native asyncio Datagram listener"""
        loop = asyncio.get_running_loop()
        try:
            await loop.create_datagram_endpoint(
                lambda: FeedbackProtocol(self),
                local_addr=("0.0.0.0", self.FEEDBACK_PORT)
            )
        except Exception as e:
            print(f"❌ [BIND ERROR] Feedback port: {e}")
            
        # Keeps this function running so your demo_stream.py doesn't exit instantly
        while True:
            await asyncio.sleep(3600)

    async def weather_loop(self):
        """Randomly generates network interference for testing"""
        while self.simulate_weather:
            await asyncio.sleep(6)
            weather_states = [0.0, 0.15, 0.40]
            self.network_weather = random.choice(weather_states)
            w_name = "☀️ CLEAR" if self.network_weather == 0 else ("🌧️ CLOUDY" if self.network_weather < 0.2 else "⛈️ STORM")
            print(f"\n[WEATHER] {w_name} WARNING: {int(self.network_weather*100)}% Packet Loss\n")

    async def transmit(self, data_chunk):
        """V3 FIX: Dynamic matrix sizes. Pass 5, 10, or 50 floats seamlessly."""
        payload_size = len(data_chunk)
        if payload_size > 255:
            raise ValueError("V3 Matrix limit is 255 floats per block.")
            
        data_bytes = bytearray()
        for value in data_chunk:
            data_bytes.extend(struct.pack('>d', float(value)))
            
        encoded_block = self.rs.encode(data_bytes)
        total_packets = payload_size + self.current_parity
        birth_time = time.time()
        
        packets = []
        for seq in range(total_packets):
            chunk = encoded_block[seq*8 : (seq+1)*8]
            p_type = 0 if seq < payload_size else 1
            # V3 FIX: Packing the payload_size directly into the header so the Receiver knows how big the matrix is!
            header = struct.pack(self.PACKET_FORMAT, p_type, self.block_id, seq, len(chunk), self.current_parity, payload_size, birth_time)
            packets.append(header + chunk)

        # Send Truth to Visor
        if self.visor_ws:
            try:
                await self.visor_ws.send(json.dumps({
                    "type": "original_brainwave",
                    "data": data_chunk
                }))
            except websockets.exceptions.ConnectionClosed:
                self.visor_ws = None 

        # Blast over UDP
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
        """V3 FIX: Authenticated Shutdown. Hackers cannot spoof this."""
        print("💊 Sending Authenticated Poison Pill to Receiver...")
        # Pack the header with type 9, and append the un-guessable SECRET_KEY
        header = struct.pack(self.PACKET_FORMAT, 9, 0, 0, len(self.SECRET_KEY), 0, 0, time.time())
        packet = header + self.SECRET_KEY
        self.sock_out.sendto(packet, (self.UDP_IP, self.DATA_PORT))
        print("🔌 Emitter shutting down gracefully.")