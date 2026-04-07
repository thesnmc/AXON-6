# AXON-6 Telemetry Engine | Copyright (c) 2026 thesnmc | MIT License
import edfio

print("🔍 Scanning clinical EDF header...")
edf = edfio.read_edf("brainwave_sample.edf")

# Target the first brainwave channel
signal = edf.signals[0]

total_floats = len(signal.data)
sampling_rate = signal.sampling_frequency
duration_sec = total_floats / sampling_rate

print("\n📊 EDF DATA VAULT OPENED:")
print(f"Channel Name:      {signal.label}")
print(f"Sampling Rate:     {sampling_rate} Hz (readings per second)")
print(f"Total Data Points: {total_floats:,} microvoltage readings")
print(f"Total Duration:    {duration_sec / 60:.2f} minutes")
print(f"AXON-6 Blocks:     {total_floats // 5:,} blocks to broadcast")