# hik_log_dump_raw

A simple Python script to extract and dump raw logs from Hikvision devices.

## Features

- Connects to Hikvision devices via ISAPI.
- Downloads and saves raw log data.
- Supports command-line usage.

## Requirements

- Python 3.6+
- `requests` library

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python.exe hik_log_dump_raw.py 0.0.0.0 admin 2025-05-16 2025-05-16 -o output.xml
```

### Options

--HOST   – IP/host name of the NVR (e.g.10.10.10.10)
--USER   – user name (Digest auth)
--START  – start of time span (YYYY‑MM‑DD *or* full ISO «YYYY‑MM‑DDTHH:MM»)
--END    – end   of time span (same format as START, inclusive)


## License

MIT License

---

*This project is not affiliated with Hikvision.*