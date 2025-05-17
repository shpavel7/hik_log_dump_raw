# hik_log_dump_raw

A simple Python script to extract and dump raw logs from Hikvision devices.

## Features

- Connects to Hikvision devices via ISAPI.
- Downloads and saves raw log data.
- Supports command-line usage.

## Requirements

- Python 3.6+
- `requests` library


## Usage

```bash
python.exe hik_log_dump_raw.py 0.0.0.0 admin 2025-05-16 2025-05-16 -o output.xml
```

### Command-line options

| Option     | Purpose                                            | Example                |
|------------|----------------------------------------------------|------------------------|
| `--HOST`   | IP address or hostname of the NVR                  | `10.10.10.10`          |
| `--USER`   | Username for HTTP **Digest** authentication        | `admin`                |
| `--START`  | Start of time span – `YYYY-MM-DD` *or* ISO `YYYY-MM-DDTHH:MM` | `2025-05-01T00:00` |
| `--END`    | End of time span (inclusive) – same format as `--START` | `2025-05-08`        |

## License

MIT License

---

*This project is not affiliated with Hikvision.*