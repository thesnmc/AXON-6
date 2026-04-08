import asyncio
import edfio
from axon6.emitter import AxonEmitter

async def run_demo():
    print("🧠 Loading clinical EEG data...")
    edf = edfio.read_edf("brainwave_sample.edf")
    brain_signal = edf.signals[0].data

    # 1. Initialize your new production Emitter!
    engine = AxonEmitter(simulate_weather=True)
    await engine.connect_visor()

    # 2. Start the background tasks (Feedback & Weather)
    asyncio.create_task(engine.listen_for_feedback())
    asyncio.create_task(engine.weather_loop())

    # 3. Feed the data to the engine
    for i in range(0, len(brain_signal) - 5, 5):
        chunk = [brain_signal[i+j] for j in range(5)]
        
        await engine.transmit(chunk)  # Just one line to heal and transmit!
        await asyncio.sleep(0.1)

    engine.send_poison_pill()

if __name__ == "__main__":
    asyncio.run(run_demo())