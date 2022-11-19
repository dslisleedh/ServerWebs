import tensorflow
from tensorflow.keras.callbacks import Callback
from tensorflow.python.util.tf_export import keras_export
import numpy as np

import logging
import requests


@keras_export("keras.callbacks.RemoteMonitorCustom")
class RemoteMonitorCustom(Callback):
    def __init__(
        self,
        name: str,
        root="http://localhost:25005",
        path="/trainlog/post_logs",
    ):
        super().__init__()
        self.name = name
        self.root = root
        self.path = path

        assert self.name not in requests.get(root + "/trainlog/check_keys"), "Job name already exists in server, got {}".format(self.name)

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
        try:
            requests.post(
                self.root + self.path,
                json={'data': send}
            )

        except requests.exceptions.RequestException:
            logging.warning(
                "Warning: could not reach RemoteMonitor "
                "root server at " + str(self.root)
            )
