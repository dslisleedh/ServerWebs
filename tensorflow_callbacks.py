import tensorflow
from tensorflow.keras.callbacks import Callback
import numpy as np

import logging
import requests


def check_train_name(name: str):
    assert name not in requests.get(
        root + "/trainlog/check_keys"), "Job name already exists in server, got {}".format(name)


def send_train_log(log: dict, root: str = "http://localhost:25005", path: str = "/trainlog/post_logs"):
    assert "name" in log.keys(), "Log must have 'name' key"
    assert "epoch" in log.keys(), "Log must have 'epoch' key"

    try:
        requests.post(root + path, json={'data': send})

    except requests.exceptions.RequestException:
        logging.warning(
            "Warning: could not reach RemoteMonitor "
            "root server at " + str(root)
        )


def send_train_end_log(name: str, root: str = "http://localhost:25005"):
    requests.post(root + "/trainlog/post_logs_end", json={'data': name})


class RemoteMonitorCustom(Callback):
    def __init__(
        self, name: str, root: str = "http://localhost:25005", path: str = "/trainlog/post_logs",
    ):
        super().__init__()
        self.name = name
        self.root = root
        self.path = path

        check_train_name(name)

    def on_epoch_end(self, epoch, logs=None):
        if requests is None:
            raise ImportError("RemoteMonitor requires the `requests` library.")
        logs = logs or {}
        send = {}
        send["name"] = self.name
        send["epoch"] = epoch
        for k, v in logs.items():
            # np.ndarray and np.generic are not scalar types
            # therefore we must unwrap their scalar values and
            # pass to the json-serializable dict 'send'
            if isinstance(v, (np.ndarray, np.generic)):
                send[k] = v.item()
            else:
                send[k] = v

        send_train_log(send, self.root, self.path)


    def on_train_end(self, logs=None):
        send_train_end_log(self.name, self.root)
