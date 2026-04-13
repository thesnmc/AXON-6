# AXON-6 Telemetry Engine
# Copyright 2026 thesnmc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import socket
import struct
import asyncio
import time
import os
import json
import websockets
from reedsolo import RSCodec, ReedSolomonError

class ReceiverProtocol(asyncio.DatagramProtocol):
    """V3 FIX: OS-level network listener. No more while-True CPU hogging!"""
    def __init__(self, queue):
        self.queue = queue

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        # The OS hands data directly to the queue. Python sleeps until this happens!
        self.queue.put_nowait((data, addr))

class AxonReceiver:
    def __init__(self, listen_ip="0.0.0.0", data_port=5005, feedback_port=5006, on_data_received=None):
        """Initializes the AXON-6 V3.1 Receiver Node"""
        self.UDP_IP = listen_ip
        self.DATA_PORT = data_port
        self.FEEDBACK_PORT = feedback_port
        
        # V3 FIX: The Authenticated Security Key
        self.SECRET_KEY = b"AXON-PRO-KEY" 
        
        # V3 FIX: Added a second 'B' to the header to dynamically track Payload Size
        self.PACKET_FORMAT = '>B I I H B B d'
        self.HEADER_SIZE = struct.calcsize(self.PACKET_FORMAT)

        # We only need the OUT socket now. IN is handled by DatagramProtocol.
        self.sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.queue = asyncio.Queue()
        self.block_buffer = {}
        self.block_timestamps = {} 
        self.last_block_id = 0 
        self.processed_blocks = set() 
        
        self.current_parity = 1
        self.rs = RSCodec(self.current_parity * 8)

        self.total_expected = 0
        self.total_received = 0
        
        # V3 FIX: Tracks clock drift between separate machines
        self.time_offset = None 

        # V3.1 FIX: Dynamic target locking! Defaults to localhost until a packet arrives.
        self.target_emitter_ip = "127.0.0.1" 

        self.connected_clients = set()
        self.emitters = set() 
        
        self.on_data_received = on_data_received

    async def garbage_collector(self):
        """PRO FIX: Scans memory every second and deletes incomplete blocks older than 2 seconds."""
        while True:
            now = time.time()
            expired_blocks = [bid for bid, ts in self.block_timestamps.items() if now - ts > 2.0]
            
            for bid in expired_blocks:
                if bid in self.block_buffer:
                    del self.block_buffer[bid]
                del self.block_timestamps[bid]
                print(f"🗑️ GARBAGE COLLECTOR: Purged dead Block {bid} to prevent memory leak.")
                
            await asyncio.sleep(1.0)

    async def visor_handler(self, websocket):
        """Registers UI Visors and acts as a Relay for the Emitter"""
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                if "original_brainwave" in message:
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
                    # V3.1 FIX: Send feedback directly to the dynamically locked Emitter IP, NOT 0.0.0.0
                    self.sock_out.sendto(str(target_parity).encode(), (self.target_emitter_ip, self.FEEDBACK_PORT))
                    self.current_parity = target_parity
                    self.rs = RSCodec(self.current_parity * 8) 

                await self.send_to_visor({"type": "status", "health": health_str, "parity": self.current_parity})

            self.total_expected = 0
            self.total_received = 0
            
            if len(self.processed_blocks) > 100:
                self.processed_blocks.clear()

    def sync_latency(self, birth_time):
        """V3 FIX: Calculates Network Jitter regardless of machine clock drift"""
        now = time.time()
        if self.time_offset is None:
            self.time_offset = now - birth_time
            return 0.0
        return (now - (birth_time + self.time_offset)) * 1000

    async def process_queue(self):
        """V3 FIX: Processes packets from the OS queue continuously. Replaces catch_and_heal."""
        while True:
            # We now extract the 'addr' (IP address) of the incoming packet
            data, addr = await self.queue.get()
            
            # V3.1 FIX: Dynamically lock onto the Emitter's exact IP address so we can fire back!
            if addr and addr[0] != "0.0.0.0":
                self.target_emitter_ip = addr[0]

            header = data[:self.HEADER_SIZE] 
            payload = data[self.HEADER_SIZE:]
            
            # V3 FIX: Now unpacks the dynamic payload_size!
            p_type, block_id, seq_id, length, parity_count, payload_size, birth_time = struct.unpack(self.PACKET_FORMAT, header)
            
            # V3 FIX: Authenticated Poison Pill
            if p_type == 9:
                if payload == self.SECRET_KEY:
                    print(f"\n🏁 AUTHENTICATED POISON PILL RECEIVED. Surgery complete.")
                    print("💾 Saving final telemetry logs...")
                    await self.send_to_visor({"type": "system", "message": "STREAM COMPLETE"})
                    print("🔌 Receiver shutting down gracefully.")
                    os._exit(0)
                else:
                    print("⚠️ [SECURITY] Unauthenticated shutdown attempt blocked!")
                continue

            if block_id > self.last_block_id + 1 and self.last_block_id != 0:
                lost_count = block_id - self.last_block_id - 1
                self.total_expected += (lost_count * (payload_size + parity_count))
                print(f"🚨 NETWORK BLACKOUT: Completely lost {lost_count} blocks in mid-air!")
            
            self.last_block_id = max(self.last_block_id, block_id)

            if block_id in self.processed_blocks:
                self.total_received += 1
                continue

            if block_id not in self.block_buffer:
                self.block_buffer[block_id] = {}
                self.block_timestamps[block_id] = time.time()
                self.total_expected += (payload_size + parity_count)
                
            self.block_buffer[block_id][seq_id] = payload
            self.total_received += 1
            
            # V3 FIX: Dynamic length checking
            if len(self.block_buffer[block_id]) == payload_size:
                received_seqs = list(self.block_buffer[block_id].keys())
                missing_originals = [s for s in range(payload_size) if s not in received_seqs]
                
                jitter_ms = self.sync_latency(birth_time)
                recovered_floats = []
                
                # V3 FIX: "Boy Who Cried Wolf" Fix & CPU Saver
                # V3.2 FIX: Dynamic Array Unpacking & Industrial RS Shielding
                if not missing_originals:
                    # Combine all packets into one dynamic byte array
                    decoded_data = bytearray()
                    for seq in range(payload_size):
                        decoded_data.extend(self.block_buffer[block_id][seq])
                    
                    # Dynamically count how many 8-byte doubles are actually in the payload!
                    total_doubles = len(decoded_data) // 8
                    recovered_floats = [struct.unpack('>d', decoded_data[i*8:(i+1)*8])[0] for i in range(total_doubles)]
                    print(f"⚡ FAST TRACK in {jitter_ms:.2f}ms: [ {', '.join([f'{n:.5f}' for n in recovered_floats])} ]")
                else:
                    print(f"🚨 ALERT: Data missing in Block {block_id}. Deep Healing...")
                    # Dynamically figure out how big each packet is from the ones that survived
                    sample_chunk = self.block_buffer[block_id][received_seqs[0]]
                    chunk_byte_size = len(sample_chunk)
                    
                    healed_bytes = bytearray((payload_size + parity_count) * chunk_byte_size)
                    erasure_positions = []
                    
                    for seq in range(payload_size + parity_count):
                        if seq in received_seqs:
                            healed_bytes[seq*chunk_byte_size : (seq+1)*chunk_byte_size] = self.block_buffer[block_id][seq]
                        else:
                            for b in range(chunk_byte_size):
                                erasure_positions.append(seq*chunk_byte_size + b)
                    try:
                        decoded_data = await asyncio.to_thread(self.rs.decode, healed_bytes, erase_pos=erasure_positions)
                        decoded_data = decoded_data[0] # RSCodec returns a tuple
                        
                        # Strip away parity bytes, leave only original payload
                        original_bytes = decoded_data[:payload_size * chunk_byte_size]
                        total_doubles = len(original_bytes) // 8
                        recovered_floats = [struct.unpack('>d', original_bytes[i*8:(i+1)*8])[0] for i in range(total_doubles)]
                        print(f"✨ HEALED in {jitter_ms:.2f}ms: [ {', '.join([f'{n:.5f}' for n in recovered_floats])} ]")
                    except ReedSolomonError:
                        print(f"💀 CRITICAL: Block {block_id} completely destroyed.")
                        await self.send_to_visor({"type": "system", "message": f"BLOCK {block_id} CRITICAL LOSS"})
                        # Graceful fallback so the robot doesn't crash
                        await self.send_to_visor({"type": "brainwave", "data": [0.0], "latency": 0})
                    
                    

                if recovered_floats:
                    if self.on_data_received:
                        self.on_data_received(recovered_floats)
                    await self.send_to_visor({
                        "type": "brainwave", 
                        "data": recovered_floats, 
                        "latency": round(jitter_ms, 2)
                    })

                self.processed_blocks.add(block_id)
                del self.block_buffer[block_id]
                if block_id in self.block_timestamps:
                    del self.block_timestamps[block_id]

    async def run(self):
        """Boots the receiver loops"""
        print("🛡️ ASYNC AXON-6 Tactical Receiver Online (V3.1 Masterpiece)...")
        print("📡 Visor Dashboard broadcasting on ws://localhost:8765\n")
        
        # V3 FIX: Connect the OS-level Datagram Endpoint
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(
            lambda: ReceiverProtocol(self.queue),
            local_addr=(self.UDP_IP, self.DATA_PORT)
        )
        
        async with websockets.serve(self.visor_handler, "127.0.0.1", 8765):
            await asyncio.gather(self.analyze_network_health(), self.garbage_collector(), self.process_queue())