# AXON-6 Telemetry Engine | Copyright (c) 2026 thesnmc | MIT License
import socket
import struct
import asyncio
import time
import os
import json
import websockets
from reedsolo import RSCodec, ReedSolomonError

class AxonReceiver:
    def __init__(self, listen_ip="127.0.0.1", data_port=5005, feedback_port=5006, on_data_received=None):
        """Initializes the AXON-6 Receiver Node"""
        self.UDP_IP = listen_ip
        self.DATA_PORT = data_port
        self.FEEDBACK_PORT = feedback_port
        self.PACKET_FORMAT = '>B I I H B d'
        self.HEADER_SIZE = 20

        self.sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_in.bind((self.UDP_IP, self.DATA_PORT))
        self.sock_in.setblocking(False)

        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.block_buffer = {}
        self.processed_blocks = set() 
        self.current_parity = 1
        self.rs = RSCodec(self.current_parity * 4)

        self.total_expected = 0
        self.total_received = 0

        self.connected_clients = set()
        self.emitters = set() 
        
        # The magic plug-and-play callback!
        self.on_data_received = on_data_received

    async def visor_handler(self, websocket):
        """Registers UI Visors and acts as a Relay for the Emitter"""
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                self.emitters.add(websocket) 
                targets = self.connected_clients - self.emitters
                if targets:
                    websockets.broadcast(targets, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.remove(websocket)
            self.emitters.discard(websocket)

    async def send_to_visor(self, payload):
        """Fires data to the HTML dashboard (safely bypassing the Emitter)"""
        targets = self.connected_clients - self.emitters
        if targets:
            message = json.dumps(payload)
            websockets.broadcast(targets, message)

    async def analyze_network_health(self):
        """Monitors packet drops and commands the Emitter to adjust shields"""
        while True:
            await asyncio.sleep(4) 
            
            if self.total_expected > 0:
                loss_rate = 1.0 - (self.total_received / self.total_expected)
                target_parity = self.current_parity
                health_str = f"{int((1.0 - loss_rate)*100)}%"
                
                if loss_rate > 0.25:
                    target_parity = 3 
                    print(f"⚠️ HEALTH REPORT: {int(loss_rate*100)}% LOSS! Ordering MAX SHIELDS (3).")
                elif loss_rate > 0.05:
                    target_parity = 2 
                    print(f"⚠️ HEALTH REPORT: {int(loss_rate*100)}% LOSS! Ordering MEDIUM SHIELDS (2).")
                elif loss_rate <= 0.05 and self.current_parity > 1: 
                    target_parity = 1 
                    print(f"✅ HEALTH REPORT: ~0% LOSS. Dropping shields to LIGHT ARMOR (1).")

                if target_parity != self.current_parity:
                    self.sock_out.sendto(str(target_parity).encode(), (self.UDP_IP, self.FEEDBACK_PORT))
                    self.current_parity = target_parity
                    self.rs = RSCodec(self.current_parity * 4) 

                await self.send_to_visor({"type": "status", "health": health_str, "parity": self.current_parity})

            self.total_expected = 0
            self.total_received = 0
            
            if len(self.processed_blocks) > 100:
                self.processed_blocks.clear()

    async def catch_and_heal(self):
        """Catches UDP packets and executes Reed-Solomon resurrection"""
        while True:
            try:
                data, _ = self.sock_in.recvfrom(1024)
                header = data[:self.HEADER_SIZE] 
                payload = data[self.HEADER_SIZE:]
                
                p_type, block_id, seq_id, length, parity_count, birth_time = struct.unpack(self.PACKET_FORMAT, header)
                
                if p_type == 9:
                    print(f"\n🏁 POISON PILL RECEIVED. Surgery complete.")
                    print("💾 Saving final telemetry logs...")
                    await self.send_to_visor({"type": "system", "message": "STREAM COMPLETE"})
                    print("🔌 Receiver shutting down gracefully.")
                    os._exit(0)

                if block_id in self.processed_blocks:
                    self.total_received += 1
                    continue

                if block_id not in self.block_buffer:
                    self.block_buffer[block_id] = {}
                    self.total_expected += (5 + parity_count)
                    
                self.block_buffer[block_id][seq_id] = payload
                self.total_received += 1
                
                if len(self.block_buffer[block_id]) == 5:
                    received_seqs = list(self.block_buffer[block_id].keys())
                    
                    if sum(1 for s in received_seqs if s < 5) < 5:
                        print(f"🚨 ALERT: Data missing in Block {block_id}. Deep Healing...")
                    
                    healed_bytes = bytearray((5 + parity_count) * 4)
                    erasure_positions = []
                    
                    for seq in range(5 + parity_count):
                        if seq in received_seqs:
                            healed_bytes[seq*4 : (seq+1)*4] = self.block_buffer[block_id][seq]
                        else:
                            for b in range(4):
                                erasure_positions.append(seq*4 + b)
                    try:
                        decoded_data, _, _ = self.rs.decode(healed_bytes, erase_pos=erasure_positions)
                        recovered_floats = [struct.unpack('>f', decoded_data[i*4:(i+1)*4])[0] for i in range(5)]
                        
                        latency_ms = (time.time() - birth_time) * 1000
                        print(f"✨ HEALED in {latency_ms:.2f}ms: [ {', '.join([f'{n:.2f}' for n in recovered_floats])} ]")
                        
                        # ⚡ FIRE THE CUSTOM CALLBACK HERE ⚡
                        if self.on_data_received:
                            self.on_data_received(recovered_floats)

                        await self.send_to_visor({
                            "type": "brainwave", 
                            "data": recovered_floats, 
                            "latency": round(latency_ms, 2)
                        })
                        
                    except ReedSolomonError:
                        print(f"💀 CRITICAL: Block {block_id} completely destroyed.")
                        await self.send_to_visor({"type": "system", "message": f"BLOCK {block_id} CRITICAL LOSS"})
                        await self.send_to_visor({"type": "brainwave", "data": [0.0, 0.0, 0.0, 0.0, 0.0], "latency": 0})

                    self.processed_blocks.add(block_id)
                    del self.block_buffer[block_id]
                    
            except BlockingIOError:
                await asyncio.sleep(0.01)

    async def run(self):
        """Boots the receiver loops"""
        print("🛡️ ASYNC AXON-6 Tactical Receiver Online...")
        print("📡 Visor Dashboard broadcasting on ws://localhost:8765\n")
        async with websockets.serve(self.visor_handler, "127.0.0.1", 8765):
            await asyncio.gather(self.analyze_network_health(), self.catch_and_heal())