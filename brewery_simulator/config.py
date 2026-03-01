from __future__ import annotations
import tomllib
from pathlib import Path


class MQTTConfig:
    def __init__(self, host="localhost", port=1883, username="", password="",
                 client_id="brewery-sim", topic_root="brewery", qos=1,
                 retain=True, keepalive=60, protocol=5, tls=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        self.topic_root = topic_root
        self.qos = qos
        self.retain = retain
        self.keepalive = keepalive
        self.protocol = protocol
        self._tls = tls or {}

    @property
    def tls_enabled(self): return self._tls.get("enabled", False)
    @property
    def tls_ca_certs(self): return self._tls.get("ca_certs", "")
    @property
    def tls_certfile(self): return self._tls.get("certfile", "")
    @property
    def tls_keyfile(self): return self._tls.get("keyfile", "")


class SimConfig:
    def __init__(self, tick_interval=1.0, default_speed=1.0,
                 heartbeat_interval=30, publish_on_change=True, random_seed=0):
        self.tick_interval = tick_interval
        self.default_speed = default_speed
        self.heartbeat_interval = heartbeat_interval
        self.publish_on_change = publish_on_change
        self.random_seed = random_seed


class BreweryConfig:
    def __init__(self, mqtt, sim, process, physics):
        self.mqtt = mqtt
        self.sim = sim
        self.process = process
        self.physics = physics


def load_config(path):
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    mqtt_raw = dict(raw.get("mqtt", {}))
    tls = mqtt_raw.pop("tls", {})
    valid = {"host","port","username","password","client_id","topic_root","qos","retain","keepalive","protocol"}
    mqtt = MQTTConfig(**{k: v for k, v in mqtt_raw.items() if k in valid}, tls=tls)
    sim_raw = raw.get("simulator", {})
    valid_sim = {"tick_interval","default_speed","heartbeat_interval","publish_on_change","random_seed"}
    sim = SimConfig(**{k: v for k, v in sim_raw.items() if k in valid_sim})
    return BreweryConfig(mqtt=mqtt, sim=sim, process=raw.get("process", {}), physics=raw.get("physics", {}))
