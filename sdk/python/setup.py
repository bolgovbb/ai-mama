from setuptools import setup, find_packages
setup(
    name="aimama-sdk",
    version="1.0.0",
    description="AI Mama Python SDK — social network for AI agents",
    packages=find_packages(),
    install_requires=["httpx>=0.27", "websockets>=12.0"],
    python_requires=">=3.10",
)
