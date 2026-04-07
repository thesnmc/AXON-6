# AXON-6 Telemetry Engine | Copyright (c) 2026 thesnmc | MIT License
import socket
import struct
import asyncio
import time
import os
import json
import websockets
from reedsolo import RSCodec, ReedSolomonError

# THE PROTOCOL SETUP
UDP_IP = "127.0.0.1"
DATA_PORT = 5005
FEEDBACK_PORT = 5006
# V1.1 FIX: Header updated to 20 bytes
PACKET_FORMAT = '>B I I H B d'
HEADER_SIZE = 20

sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_in.bind((UDP_IP, DATA_PORT))
sock_in.setblocking(False)

sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# GLOBAL STATE
block_buffer = {}
processed_blocks = set() 
current_parity = 1
rs = RSCodec(current_parity * 4)

total_expected = 0
total_received = 0

# WEBSOCKET STATE (THE VISOR)
connected_clients = set()
emitters = set() # THE FIX: Track who the Emitter is so we don't crash it!

print("🛡️ ASYNC AXON-6 Tactical Receiver Online...")
print("📡 Visor Dashboard broadcasting on ws://localhost:8765\n")

async def visor_handler(websocket):
    """Registers UI Visors and acts as a Relay for the Emitter"""
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # The moment someone sends us data, we know it's the Emitter!
            emitters.add(websocket) 
            
            # Bounce Emitter's raw truth data ONLY to the HTML Visors
            targets = connected_clients - emitters
            if targets:
                websockets.broadcast(targets, message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        emitters.discard(websocket) # Safely clean up

async def send_to_visor(payload):
    """Fires data to the HTML dashboard (safely bypassing the Emitter)"""
    targets = connected_clients - emitters
    if targets:
        message = json.dumps(payload)
        websockets.broadcast(targets, message)

async def analyze_network_health():
    global total_expected, total_received, current_parity, rs, processed_blocks
    while True:
        await asyncio.sleep(4) 
        
        if total_expected > 0:
            loss_rate = 1.0 - (total_received / total_expected)
            target_parity = current_parity
            health_str = f"{int((1.0 - loss_rate)*100)}%"
            
            if loss_rate > 0.25:
                target_parity = 3 
                print(f"⚠️ HEALTH REPORT: {int(loss_rate*100)}% LOSS! Ordering MAX SHIELDS (3).")
            elif loss_rate > 0.05:
                target_parity = 2 
                print(f"⚠️ HEALTH REPORT: {int(loss_rate*100)}% LOSS! Ordering MEDIUM SHIELDS (2).")
            elif loss_rate <= 0.05 and current_parity > 1: 
                target_parity = 1 
                print(f"✅ HEALTH REPORT: ~0% LOSS. Dropping shields to LIGHT ARMOR (1).")

            if target_parity != current_parity:
                sock_out.sendto(str(target_parity).encode(), (UDP_IP, FEEDBACK_PORT))
                current_parity = target_parity
                rs = RSCodec(current_parity * 4) 

            # Send Network status to the Visor
            await send_to_visor({"type": "status", "health": health_str, "parity": current_parity})

        total_expected = 0
        total_received = 0
        
        if len(processed_blocks) > 100:
            processed_blocks.clear()

async def catch_and_heal():
    global total_expected, total_received, rs, processed_blocks
    while True:
        try:
            data, _ = sock_in.recvfrom(1024)
            header = data[:HEADER_SIZE] 
            payload = data[HEADER_SIZE:]
            
            # Unpack the timestamp
            p_type, block_id, seq_id, length, parity_count, birth_time = struct.unpack(PACKET_FORMAT, header)
            
            # V1.1 FIX: THE KILL SWITCH
            if p_type == 9:
                print(f"\n🏁 POISON PILL RECEIVED. Surgery complete.")
                print("💾 Saving final telemetry logs...")
                await send_to_visor({"type": "system", "message": "STREAM COMPLETE"})
                print("🔌 Receiver shutting down gracefully.")
                os._exit(0)

            if block_id in processed_blocks:
                total_received += 1
                continue

            if block_id not in block_buffer:
                block_buffer[block_id] = {}
                total_expected += (5 + parity_count)
                
            block_buffer[block_id][seq_id] = payload
            total_received += 1
            
            if len(block_buffer[block_id]) == 5:
                received_seqs = list(block_buffer[block_id].keys())
                
                if sum(1 for s in received_seqs if s < 5) < 5:
                    print(f"🚨 ALERT: Data missing in Block {block_id}. Deep Healing...")
                
                healed_bytes = bytearray((5 + parity_count) * 4)
                erasure_positions = []
                
                for seq in range(5 + parity_count):
                    if seq in received_seqs:
                        healed_bytes[seq*4 : (seq+1)*4] = block_buffer[block_id][seq]
                    else:
                        for b in range(4):
                            erasure_positions.append(seq*4 + b)
                try:
                    decoded_data, _, _ = rs.decode(healed_bytes, erase_pos=erasure_positions)
                    recovered_floats = [struct.unpack('>f', decoded_data[i*4:(i+1)*4])[0] for i in range(5)]
                    
                    # V1.1 FIX: THE SPEEDOMETER
                    latency_ms = (time.time() - birth_time) * 1000
                    print(f"✨ HEALED in {latency_ms:.2f}ms: [ {', '.join([f'{n:.2f}' for n in recovered_floats])} ]")
                    
                    # THE VISOR BRIDGE: Send the healed brainwaves to the UI!
                    await send_to_visor({
                        "type": "brainwave", 
                        "data": recovered_floats, 
                        "latency": round(latency_ms, 2)
                    })
                    
                except ReedSolomonError:
                    print(f"💀 CRITICAL: Block {block_id} completely destroyed.")
                    await send_to_visor({"type": "system", "message": f"BLOCK {block_id} CRITICAL LOSS"})
                    # NEW: Push flatline to graph so you visually see the packet drop
                    await send_to_visor({"type": "brainwave", "data": [0.0, 0.0, 0.0, 0.0, 0.0], "latency": 0})

                processed_blocks.add(block_id)
                del block_buffer[block_id]
                
        except BlockingIOError:
            await asyncio.sleep(0.01)

async def main():
    # Run the WebSocket server and the UDP loops simultaneously
    async with websockets.serve(visor_handler, "127.0.0.1", 8765):
        await asyncio.gather(analyze_network_health(), catch_and_heal())

if __name__ == "__main__":
    asyncio.run(main())