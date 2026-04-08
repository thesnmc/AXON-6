from setuptools import setup, find_packages

setup(
    name="axon6",
    version="1.0.0",
    description="Real-Time, Self-Healing Neural Telemetry Protocol",
    author="thesnmc",
    url="https://github.com/thesnmc/AXON-6",
    packages=find_packages(),
    install_requires=[
        "reedsolo>=1.0.5",
        "websockets>=10.0",
        "edfio>=0.2.0"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)