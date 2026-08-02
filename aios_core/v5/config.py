from dataclasses import dataclass


@dataclass
class AIOSConfig:
    name: str = "AIOS"
    version: str = "5.0.0-alpha"
    environment: str = "development"
