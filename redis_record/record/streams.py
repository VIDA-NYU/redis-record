# Class to record all desired redis activity

import base64
import fnmatch
import time
import tqdm
import redis

from .. import util
from .recorder import Recorder
from ..config import *
from .. import ctl


def record(
        name=None, stream_ids='*', ignore_streams=[], 
        record_key=RECORD_KEY, out_dir=RECORDING_DIR, 
        stream_refresh=3000, data_block=1000, wait_block=3000, no_streams_sleep=1000,
        single_recording=None,
        host=HOST, port=PORT, db=DB
):
    '''Record redis streams to file.
    
    Arguments:
        name (str): name of the recording. Only use this if you want to start a recording when the script begins.
        stream_ids (list[str]): Stream IDs or Stream ID patterns (``["prefix:*"]``) to record. 
        ignore_streams (list[str]): Stream IDs or Stream ID patterns (``["prefix:*"]``) to ignore. 
        record_key (str): the key in redis used to store the recording name.
        out_dir (str): the directory to write recordings to.
        stream_refresh (int): the number of milliseconds between querying for new streams.
        data_block (int): How long to block for data (in milliseconds).
        wait_block (int): How long to block for recording name changes (in milliseconds). It only blocks if no recording is currently happening.
        no_streams_sleep (int): How long to sleep (in milliseconds) if no streams are available. 
    '''
    record_name = name  # 
    single_recording = bool(name) if single_recording is None else single_recording

    # initialize stream IDs
    stream_ids = (stream_ids or '*').split('+')
    stream_patterns = [s for s in stream_ids if '*' in s]
    stream_ids = [s for s in stream_ids if '*' not in s]
    tqdm.tqdm.write(f"Streams: {stream_ids}. Stream Patterns: {stream_patterns}")
    assert stream_ids or stream_patterns

    r = redis.Redis(host=host, port=port, db=db)
    pbar = tqdm.tqdm()
    try:
        with Recorder(out_dir=out_dir) as rec, r:
            # initialize cursor
            cursor = {s: '$' for s in stream_ids}
            rec_cursor = {record_key: '0'}
            
            # initialize recording state
            record_start_timestamp = None
            if record_name:
                record_start_timestamp = util.format_epoch_time(time.time())
                rec_cursor[record_key] = record_start_timestamp
                tqdm.tqdm.write(f"Starting recording: {record_name}")
                ctl.start_recording(r, record_name, record_start_timestamp)

            t0s = 0
            while True:
                # ---------------------- Watch for changes in recording ---------------------- #

                # query for recording name stream
                results, rec_cursor = util.read_latest(r, rec_cursor, block=False if record_name else wait_block)

                # check for recording changes
                for sid, xs in results:
                    if sid == record_key:
                        for t, x in xs[-1:]:
                            # get new recording name
                            x = (x.get(b'd') or b'').decode() or None

                            if record_name != x:  # idempotent

                                # ------------------------------- Finishing up ------------------------------- #

                                if record_name:  # finish up active recording
                                    rec.ensure_writer(record_name)
                                    tstamp = util.parse_epoch_time(t)

                                    while cursor:
                                        # read data from redis and write to file
                                        results, cursor = util.read_next(r, cursor, block=data_block)
                                        result_sids = {s for s, x in results if x}
                                        for sid, xs in results:
                                            rec.ensure_channel(sid)
                                            for t, x in xs:
                                                # the data is from after the recording ended.
                                                if util.parse_epoch_time(t) > tstamp:
                                                    result_sids.remove(sid)
                                                    break
                                                # write data
                                                pbar.set_description(f'{sid} {t}')
                                                rec.write(util.parse_epoch_time(t), sid, **prepare_data(x))
                                                pbar.update()

                                        # update cursor to only include active streams
                                        cursor = {k: v for k, v in cursor.items() if k in result_sids}

                                rec.close()

                                # ----------------------------- Change recording ----------------------------- #

                                record_name = x
                                record_start_timestamp = t
                                cursor = {sid: record_start_timestamp for sid in stream_ids}

                                tqdm.tqdm.write(f'{"new recording:" if record_name else "ended recording"}: {record_name} {record_start_timestamp}')

                # no recording...
                if not record_name:
                    continue

                # --------------------------- Query for new streams -------------------------- #

                # keep up-to-date list of streams
                t1s = time.time()
                if stream_patterns and t1s - t0s > stream_refresh / 1000:
                    keys = {x.decode('utf-8') for x in r.scan_iter(match=stream_ids or None, _type='stream')}
                    for k in keys - set(cursor):
                        if (
                            k != record_key and
                            not any(fnmatch.fnmatch(k, p) for p in ignore_streams) and
                            any(fnmatch.fnmatch(k, p) for p in stream_patterns)
                        ):
                            tqdm.tqdm.write(f"adding stream: {k} {record_start_timestamp}")
                            cursor[k] = record_start_timestamp
                    t0s = t1s

                # no streams to record, just wait.
                if not cursor:
                    # we sleep but we have the record start timestamp so we won't lose any data.
                    # We just can't sleep too long and fall behind
                    tqdm.tqdm.write("no cursor. sleeping")
                    time.sleep(no_streams_sleep/1000)
                    continue

                # ---------------------------- Pull data and write --------------------------- #

                # read data from redis and write to file
                results, cursor = util.read_next(r, cursor, block=data_block)
                for sid, xs in results:
                    rec.ensure_writer(record_name)
                    rec.ensure_channel(sid)
                    for t, x in xs:
                        pbar.set_description(f'{sid} {t}')
                        rec.write(util.parse_epoch_time(t), sid, stream_id=sid, data=prepare_data(x))
                        pbar.update()
    finally:
        if single_recording:
            ctl.stop_recording(r)


def prepare_data(data):
    return {k.decode(): base64.b64encode(v).decode() for k, v in data.items()}


def cli():
    import fire
    fire.Fire(record)

if __name__ == '__main__':
    from pyinstrument import Profiler
    p = Profiler()
    try:
        with p:
            cli()
    finally:
        p.print()
