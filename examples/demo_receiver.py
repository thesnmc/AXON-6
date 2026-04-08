import asyncio
from axon6.receiver import AxonReceiver

# Define what you want to do with the data when it arrives!
def my_robot_controller(healed_data):
    print(f"🤖 Sending {healed_data} to the robotic arm!")

# Plug it into the engine
engine = AxonReceiver(on_data_received=my_robot_controller)

if __name__ == "__main__":
    asyncio.run(engine.run())