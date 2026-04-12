# legacy_emitter.py | AXON-6 V3.2 Compatible Emitter
# Copyright (c) 2026 thesnmc | MIT License
import struct
import socket
import asyncio
import random
import time
import os
import json
import websockets
from reedsolo import RSCodec
import edfio

# THE PROTOCOL SETUP (V3.2 Dialect)
UDP_IP = "127.0.0.1" 
DATA_PORT = 5005
FEEDBACK_PORT = 5006
# V3.2 FIX: 21-Byte Header (p_type, block_id, seq_id, length, parity_count, payload_size, birth_time)
PACKET_FORMAT = '>B I I H B B d' 

# GLOBAL STATE
current_parity = 1 
# V3.2 FIX: Doubles are 8 bytes, so 1 parity packet = 8 bytes of armor
rs = RSCodec(current_parity * 8) 
network_weather = 0.0 

sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_in.bind((UDP_IP, FEEDBACK_PORT))
sock_in.setblocking(False) 

async def listen_for_feedback():
    global current_parity, rs
    while True:
        try:
            data, _ = sock_in.recvfrom(1024)
            new_parity = int(data.decode())
            if new_parity != current_parity:
                current_parity = new_parity
                rs = RSCodec(current_parity * 8) # Update armor size
                print(f"🔄 EMITTER ADAPTED: Matrix shifted to {current_parity} Parity Packets.\n")
        except BlockingIOError:
            pass
        await asyncio.sleep(0.1)

async def simulate_weather():
    global network_weather
    while True:
        await asyncio.sleep(6)
        weather_states = [0.0, 0.15, 0.40] 
        network_weather = random.choice(weather_states)
        weather_name = "☀️ CLEAR" if network_weather == 0 else ("🌧️ CLOUDY" if network_weather < 0.2 else "⛈️ STORM")
        print(f"\n==================================================")
        print(f"{weather_name} WARNING: {int(network_weather*100)}% Packet Loss")
        print(f"==================================================\n")

async def broadcast_brainwaves():
    print("🧠 Loading clinical EEG data...")
    # THE BULLETPROOF FIX: Dynamically find the file path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    edf_path = os.path.join(current_dir, "brainwave_sample.edf")
    edf = edfio.read_edf(edf_path)
    brain_signal = edf.signals[0].data
    print("🚀 ASYNC AXON-6 Emitter Online...")

    # LINK TO VISOR (Websocket Client)
    visor_ws = None
    try:
        visor_ws = await websockets.connect("ws://127.0.0.1:8765")
        print("🔗 Uplink established with Visor Dashboard.")
    except Exception:
        print("⚠️ Visor Dashboard offline. Running blind.")

    block_id = 1
    for i in range(0, len(brain_signal) - 5, 5):
        data_bytes = bytearray()
        for j in range(5):
            # V3.2 FIX: Pack as 8-byte Doubles ('>d')
            data_bytes.extend(struct.pack('>d', float(brain_signal[i+j])))
        
        encoded_block = rs.encode(data_bytes)
        total_packets = 5 + current_parity
        
        birth_time = time.time()
        
        packets = []
        for seq in range(total_packets):
            # V3.2 FIX: Chunks are now 8 bytes wide
            chunk = encoded_block[seq*8 : (seq+1)*8]
            p_type = 0 if seq < 5 else 1
            # V3.2 FIX: Added '5' to the header to declare the payload_size!
            packet = struct.pack(PACKET_FORMAT, p_type, block_id, seq, len(chunk), current_parity, 5, birth_time) + chunk
            packets.append(packet)

        # Unpack the original doubles so we can print what we sent
        original_floats = [struct.unpack('>d', data_bytes[k*8:(k+1)*8])[0] for k in range(5)]
        float_str = f"[ {', '.join([f'{n:.2f}' for n in original_floats])} ]"

        # SEND TRUTH DATA TO VISOR
        if visor_ws:
            try:
                await visor_ws.send(json.dumps({
                    "type": "original_brainwave",
                    "data": original_floats
                }))
            except websockets.exceptions.ConnectionClosed:
                visor_ws = None 

        destroyed = []
        for seq, packet in enumerate(packets):
            if random.random() > network_weather:
                sock_out.sendto(packet, (UDP_IP, DATA_PORT))
            else:
                destroyed.append(seq)
                
        if destroyed:
            print(f"🔥 BLOCK {block_id}: Weather destroyed packets {destroyed}! Sent: {float_str}")
        else:
            print(f"✅ BLOCK {block_id}: Perfect transmission. Sent: {float_str}")
            
        block_id += 1
        await asyncio.sleep(0.1) # Accelerated to 10 FPS for the visualizer

    # THE KILL SWITCH
    print("\n🏁 EOF REACHED. Clinical data stream complete.")
    print("💊 Sending Poison Pill (p_type=9) to Receiver...")
    # V3.2 FIX: Added the extra 0 for payload_size in the poison pill
    poison_pill = struct.pack(PACKET_FORMAT, 9, 0, 0, 0, 0, 0, time.time())
    sock_out.sendto(poison_pill, (UDP_IP, DATA_PORT))
    print("🔌 Emitter shutting down gracefully.")
    os._exit(0) 

async def main():
    await asyncio.gather(listen_for_feedback(), simulate_weather(), broadcast_brainwaves())

if __name__ == "__main__":
    asyncio.run(main())