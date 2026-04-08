import asyncio
from axon6.receiver import AxonReceiver

# Define what you want to do with the data when it arrives!
def my_robot_controller(healed_data):
    # This proves the 64-bit Double Precision is working!
    print(f"🤖 Sending {healed_data} to the robotic arm!")

async def main():
    # Plug it into the engine
    engine = AxonReceiver(on_data_received=my_robot_controller)
    await engine.run()

if __name__ == "__main__":
    asyncio.run(main())