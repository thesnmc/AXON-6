# AXON-6 Telemetry Engine | Copyright (c) 2026 thesnmc | MIT License
import struct
import socket
import asyncio
import random
import time
import json
import websockets
from reedsolo import RSCodec

class AxonEmitter:
    def __init__(self, target_ip="127.0.0.1", data_port=5005, feedback_port=5006, simulate_weather=False):
        """Initializes the AXON-6 Emitter Node"""
        self.UDP_IP = target_ip
        self.DATA_PORT = data_port
        self.FEEDBACK_PORT = feedback_port
        self.PACKET_FORMAT = '>B I I H B d'
        
        self.current_parity = 1
        self.rs = RSCodec(self.current_parity * 4)
        
        self.simulate_weather = simulate_weather
        self.network_weather = 0.0
        
        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_in.bind((self.UDP_IP, self.FEEDBACK_PORT))
        self.sock_in.setblocking(False)
        
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
        """Listens for parity upgrade/downgrade orders from the Receiver"""
        while True:
            try:
                data, _ = self.sock_in.recvfrom(1024)
                new_parity = int(data.decode())
                if new_parity != self.current_parity:
                    self.current_parity = new_parity
                    self.rs = RSCodec(self.current_parity * 4)
                    print(f"🔄 EMITTER ADAPTED: Matrix shifted to {self.current_parity} Parity Packets.")
            except BlockingIOError:
                pass
            await asyncio.sleep(0.1)

    async def weather_loop(self):
        """Randomly generates network interference for testing"""
        while self.simulate_weather:
            await asyncio.sleep(6)
            weather_states = [0.0, 0.15, 0.40]
            self.network_weather = random.choice(weather_states)
            w_name = "☀️ CLEAR" if self.network_weather == 0 else ("🌧️ CLOUDY" if self.network_weather < 0.2 else "⛈️ STORM")
            print(f"\n[WEATHER] {w_name} WARNING: {int(self.network_weather*100)}% Packet Loss\n")

    async def transmit(self, data_chunk):
        """Encodes and blasts an array of 5 floats over the UDP matrix"""
        if len(data_chunk) != 5:
            raise ValueError("AXON-6 requires data chunks of exactly 5 floats.")
            
        data_bytes = bytearray()
        for value in data_chunk:
            data_bytes.extend(struct.pack('>f', float(value)))
            
        encoded_block = self.rs.encode(data_bytes)
        total_packets = 5 + self.current_parity
        birth_time = time.time()
        
        packets = []
        for seq in range(total_packets):
            chunk = encoded_block[seq*4 : (seq+1)*4]
            p_type = 0 if seq < 5 else 1
            # Pack the timestamp into the 20-byte header
            packet = struct.pack(self.PACKET_FORMAT, p_type, self.block_id, seq, len(chunk), self.current_parity, birth_time) + chunk
            packets.append(packet)

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
        
        float_str = f"[ {', '.join([f'{n:.2f}' for n in data_chunk])} ]"
        if destroyed:
            print(f"🔥 BLOCK {self.block_id}: Weather destroyed packets {destroyed}! Sent: {float_str}")
        else:
            print(f"✅ BLOCK {self.block_id}: Perfect transmission. Sent: {float_str}")
            
        self.block_id += 1

    def send_poison_pill(self):
        """Cleanly kills the stream and shuts down the Receiver"""
        print("💊 Sending Poison Pill (p_type=9) to Receiver...")
        poison_pill = struct.pack(self.PACKET_FORMAT, 9, 0, 0, 0, 0, time.time())
        self.sock_out.sendto(poison_pill, (self.UDP_IP, self.DATA_PORT))
        print("🔌 Emitter shutting down gracefully.")