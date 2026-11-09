from setuptools import setup, find_packages

setup(
    name="streamapp-expert",
    version="2.0.0",
    description="Deterministic Multi-Agent Harness for OTT, Media3, Android TV & Mobile Streaming Apps",
    author="StreamAppExpert Team",
    packages=find_packages(),
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "stream-harness=harness.cli:main",
        ],
    },
)
