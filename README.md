# Redis Record

This lets you record redis streams and commands so that you can replay them easily at a later time.

Under the hood, it uses [mcap](https://mcap.dev/docs/python/) as a storage format.

## Getting Started - Using Python

To install the redis-record package:
```bash
pip install git+https://github.com/beasteers/redis-record.git
```

### Configuring your environment

By default, we assume that redis is accessible via localhost:6379, but if that's not the case you can change that quite easily.
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
```
Each command can also accept `--host localhost --port 6379` arguments as well.

### Record

To start an on-demand recording:
```bash
python -m redis_record.record my_recording
```
To stop, just Interrupt the script (Ctrl-C).

This will create a file at `./recordings/my_recording.mcap`.

### Replay

To replay the file into the system, do:
```bash
python -m redis_record.replay my_recording
```

### What did I record last week?

List recording names.
```bash
python -m redis_record list
```

Get info about a recording.
```bash
python -m redis_record info my_recording
```

## Getting Started - Using Docker

The recorder is designed to be a long-running process, meaning that you can deploy it as a docker container and just control it using redis commands.

This is useful if you want to be able to control the recording remotely and always have the data save to the same place.

```bash
git clone https://github.com/beasteers/redis-record.git
cd redis-record

docker-compose up -d
# to observe the recording process
docker logs redis-record
```

### Record

To start a recording, do:
```bash
python -m redis_record start my_second_recording
```

To stop a recording, do:
```bash
python -m redis_record stop my_second_recording
```

### Replay

Currently, the replay container isn't a long-running container so you still need to invoke it like above:
```bash
python -m redis_record.replay my_recording
```

## Recording more than streams

The previous method is designed to capture XADD commands (data added to Redis streams). If you want to capture 
other redis commands, we can leverage Redis's MONITOR command to capture all commands.

### Record

```bash
python redis_record.record.monitor my_other_recording
```

By default, it will capture any of the SET command variants (`xadd, set, hmset, hset, hsetnx, lset, mset, msetnx, psetex, setbit, setrange, setex, setnx, getset, json.set, json.mset`), but it's easy enough to change! 


```bash
python redis_record.record.monitor my_other_recording --record-cmds '[xadd,set]'
```
I was initially going to just do `[xadd,set]` but figured trying to cover a more general use case as a default would be better.


### Replay

To replay:

```bash
python redis_record.replay.monitor my_other_recording
```

## TODOs
 - recording expiration (auto-stop a recording after e.g. 1 minute of inactivity)
 - s3 recording file storage
 - alternative exporters - e.g. mp4 - but would need consistent/general format.
 - persistent replay container - replay key controller
 - replay lock - don't allow two concurrent replays
