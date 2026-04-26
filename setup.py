from setuptools import setup, find_packages

setup(
    name="dash_exporter",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "discord.py>=2.4.0",
        "pytz>=2024.1",
    ],
)
