import os
import zipfile
from .base import BaseRecorder
from ...util import format_epoch_time, move_with_suffix

MB = 1024 * 1024

class ZipRecorder(BaseRecorder):
    def __init__(self, out_dir='.', max_len=1000, max_size=9.5*MB):
        super().__init__()
        self.out_dir = out_dir
        self.max_len = max_len
        self.max_size = max_size
        self.recording_dir = None
        self.writer = None

    def write(self, stream_id, timestamp, data):
        assert set(data) == {b'd'}, f"zip recorder can only record a single field in a stream. got {set(data)}"
        self.ensure_channel(stream_id)
        self.writer[stream_id].write(data[b'd'], format_epoch_time(timestamp))

    def close(self):
        if self.writer:
            for _, w in self.writer.items():
                w.close()
        self.writer = None

    def ensure_writer(self, record_name, force=False):
        if self.writer is not None and force:
            self.close()
        if self.writer is None:
            self.writer = {}
            self.recording_dir = os.path.join(self.out_dir, record_name)
            move_with_suffix(self.recording_dir)
            os.makedirs(self.recording_dir, exist_ok=True)
        return self

    def ensure_channel(self, channel):
        if channel not in self.writer:
            out_dir = os.path.join(self.recording_dir, channel)
            self.writer[channel] = ZipWriter(out_dir, self.max_len, self.max_size)


MB = 1024 * 1024

class ZipWriter:
    def __init__(self, out_dir, max_len=1000, max_size=9.5*MB):
        super().__init__()
        self.buffer = []
        self.out_dir = out_dir
        self.max_len = max_len
        self.max_size = max_size
        self.size = 0

    def __enter__(self):
        pass

    def __exit__(self, e, t, tb):
        self.close()

    def write(self, data, ts):
        self.size += len(data)
        self.buffer.append([data, ts])
        if len(self.buffer) >= self.max_len or self.size >= self.max_size:
            self._dump(self.buffer)
            self.size = 0

    def _dump(self, data):
        if not data:
            return
        os.makedirs(self.out_dir, exist_ok=True)
        fname = os.path.join(self.out_dir, f'{data[0][1]}_{data[-1][1]}.zip')
        with zipfile.ZipFile(fname, 'a', zipfile.ZIP_STORED, False) as zf:
            for d, ts in data:
                zf.writestr(ts, d)
        data.clear()

    def close(self):
        if self.buffer:
            self._dump(self.buffer)
