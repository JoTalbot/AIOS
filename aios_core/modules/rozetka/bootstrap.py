"""Rozetka bootstrap — doctor, preflight, calibration scaffold."""

from aios_core.modules.olx.bootstrap import OLXBootstrap


class RozetkaBootstrap(OLXBootstrap):
    """Bootstrap для rozetka.ua: doctor, preflight, calibration.

    Наследует OLXBootstrap, переопределяя package на com.rozetka.
    """

    PACKAGE = "com.rozetka"
