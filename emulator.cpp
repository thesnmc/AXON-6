/* AXON-6 C++ Emulator | FULL AUTO UPGRADE | Apache 2.0 License */

#include <iostream>
#include <vector>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <chrono>
#include <cmath> // We need this for the Sine Waves!

#pragma comment(lib, "ws2_32.lib")

#pragma pack(push, 1)
struct AxonHeader {
    uint8_t  p_type;        
    uint32_t block_id;      
    uint32_t seq_id;        
    uint16_t chunk_len;     
    uint8_t  parity_count;  
    uint8_t  payload_size;  
    double   birth_time;    
};
#pragma pack(pop)

double flip_double(double value) {
    union { double d; char bytes[8]; } src, dst;
    src.d = value;
    for (int i = 0; i < 8; i++) dst.bytes[i] = src.bytes[7 - i];
    return dst.d;
}

int main() {
    std::cout << "🚀 FULL AUTO MATRIX ENGAGED. Press Ctrl+C to stop." << std::endl;

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) return 1;

    SOCKET udp_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    sockaddr_in receiver_addr;
    receiver_addr.sin_family = AF_INET;
    receiver_addr.sin_port = htons(5005);
    receiver_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    uint32_t current_block = 1001;
    double time_counter = 0.0;

    // THE FULL-AUTO LOOP
    while (true) {
        AxonHeader header;
        header.p_type = 1;
        header.block_id = htonl(current_block); 
        header.seq_id = htonl(0);
        header.chunk_len = htons(5); 
        header.parity_count = 0;     
        header.payload_size = 1;     
        
        auto now = std::chrono::system_clock::now().time_since_epoch();
        double current_time = std::chrono::duration<double>(now).count();
        header.birth_time = flip_double(current_time);

        // Generate "Breathing" Brainwaves using Math
        std::vector<double> fake_brainwaves = {
            42.0 + (sin(time_counter) * 20.0),       // Wave 1: Swings up and down
            -17.5 + (cos(time_counter * 0.5) * 10.0), // Wave 2: Slower swing
            99.9,                                    // Wave 3: Flatline
            0.0,
            3.14
        };
        
        for(int i = 0; i < 5; i++) {
            fake_brainwaves[i] = flip_double(fake_brainwaves[i]);
        }

        int total_size = sizeof(header) + (fake_brainwaves.size() * sizeof(double));
        char* packet = new char[total_size];
        
        memcpy(packet, &header, sizeof(header));
        memcpy(packet + sizeof(header), fake_brainwaves.data(), fake_brainwaves.size() * sizeof(double));

        sendto(udp_socket, packet, total_size, 0, (sockaddr*)&receiver_addr, sizeof(receiver_addr));
        
        delete[] packet;
        
        current_block++;
        time_counter += 0.1; // Push time forward for the sine wave

        // CRITICAL: Throttle the engine to ~60 Frames Per Second.
        // If we don't do this, C++ will fire 500,000 packets a second and melt your RAM.
        Sleep(16); 
    }

    closesocket(udp_socket);
    WSACleanup();
    return 0;
}