import asyncio
import edfio
from axon6.emitter import AxonEmitter

async def run_demo():
    print("🧠 Loading clinical EEG data...")
    edf = edfio.read_edf("examples/brainwave_sample.edf")
    brain_signal = edf.signals[0].data

    # 1. Initialize your new V3 production Emitter!
    engine = AxonEmitter(simulate_weather=True)
    await engine.connect_visor()

    # 2. Start the background tasks (Feedback & Weather)
    asyncio.create_task(engine.listen_for_feedback())
    asyncio.create_task(engine.weather_loop())

    print("🚀 Commencing V3.0 Clinical Telemetry Stream...")
    await asyncio.sleep(2) # Give the receiver 2 seconds to boot

    # 3. Feed the EDF data to the engine
    for i in range(0, len(brain_signal) - 5, 5):
        chunk = [brain_signal[i+j] for j in range(5)]
        
        await engine.transmit(chunk)  
        await asyncio.sleep(0.1)

    engine.send_poison_pill()

if __name__ == "__main__":
    asyncio.run(run_demo())