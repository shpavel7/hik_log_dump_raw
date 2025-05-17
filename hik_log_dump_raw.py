#!/usr/bin/env python3
"""
hik_log_dump_raw.py  – Download **all** log rows from a Hikvision NVR/DVR and
save the *raw* CMSearch XML to a single file (no parsing).

The recorder only allows **20 pages** per CMSearch job.  Each page contains
*maxResults* rows, so with the default 100 you receive up‑to 2 000 rows.  This
script automatically:
  • raises *maxResults* if you ask for it (``--batch``)
  • detects when the 20‑page ceiling truncates a window
  • splits the time window in half and retries recursively until every chunk
    fits under the limit

Usage
-----
    python hik_log_dump_raw.py HOST USER START END [options]

Positional arguments
-------------------
HOST   – IP/host name of the NVR (e.g. 10.97.71.200)
USER   – user name (Digest auth)
START  – start of time span (YYYY‑MM‑DD *or* full ISO «YYYY‑MM‑DDTHH:MM»)
END    – end   of time span (same format as START, inclusive)

Options
-------
 -o FILE, --out FILE   output filename (default: hik_logs_raw.xml)
 --batch N             rows per page (default 100).  Try 256/512/1024 to
                       squeeze more rows into the 20‑page window.
 --insecure            skip TLS verification (NVRs usually speak plain HTTP)

Example
-------
    python hik_log_dump_raw.py 10.97.71.200 admin 2025-05-08 2025-05-08 \
           -o 2025‑05‑08.xml --batch 512
"""

from __future__ import annotations

import argparse, datetime as dt, getpass, uuid, logging, sys
import requests
from requests.auth import HTTPDigestAuth
from pathlib import Path

# ──────────────────────────────── configuration ───────────────────────────────
URL_TMPL      = "http://{}/ISAPI/ContentMgmt/logSearch"
MAX_PAGES     = 20     # firmware limit per CMSearch job
DEFAULT_BATCH = 100

HEADERS = {
    "Content-Type"    : "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept"          : "*/*",
}

XML_TMPL = """<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<CMSearchDescription>\n    <searchID>{sid}</searchID>\n    <metaId>log.std-cgi.com</metaId>\n    <timeSpanList>\n        <timeSpan>\n            <startTime>{start}</startTime>\n            <endTime>{end}</endTime>\n        </timeSpan>\n    </timeSpanList>\n    <maxResults>{batch}</maxResults>\n    {position}\n</CMSearchDescription>"""

# ─────────────────────────── helpers / low‑level calls ─────────────────────────

def build_body(sid: str, start_iso: str, end_iso: str,
               pos: int | None, batch: int) -> str:
    """Return the CMSearch POST body."""
    pos_xml = f"<searchResultPostion>{pos}</searchResultPostion>" if pos is not None else ""
    return XML_TMPL.format(sid=sid, start=start_iso, end=end_iso,
                           batch=batch, position=pos_xml)


def cmsearch(host: str, sess: requests.Session, body: str,
             verify_ssl: bool) -> tuple[bytes, int, bool]:
    """Run a single CMSearch POST and return (xml_bytes, rows_found, empty_flag)."""
    r = sess.post(URL_TMPL.format(host), data=body.encode(), headers=HEADERS,
                  timeout=15, verify=verify_ssl)
    r.raise_for_status()
    xml_bytes = r.content
    rows = xml_bytes.count(b"<searchMatchItem")
    return xml_bytes, rows, rows == 0


def dump_window(host: str, sess: requests.Session, sid: str,
                start_iso: str, end_iso: str, outfile, batch: int,
                verify_ssl: bool) -> bool:
    """Download one time window.  Returns True when completed without
    truncation, False if we hit the 20‑page ceiling (=> caller must split).
    """
    pos   : int | None = None
    pages = 0

    while True:
        body = build_body(sid, start_iso, end_iso, pos, batch)
        xml, rows, empty = cmsearch(host, sess, body, verify_ssl)

        if empty:
            break             # no more data in this window

        outfile.write(xml)
        outfile.write(b"\n")  # simple separator

        pages += 1
        if pages == MAX_PAGES:
            return False      # got truncated – must split

        pos = pages * batch   # next page

    return True               # window finished normally


# ────────────────────────────── recursive walker ──────────────────────────────

def walk_time_range(host: str, user: str, pwd: str,
                    start_dt: dt.datetime, end_dt: dt.datetime,
                    outfile, *, batch: int = DEFAULT_BATCH,
                    verify_ssl: bool = True) -> None:
    """Recursively walk [start_dt, end_dt) downloading all logs to *outfile*."""
    sess = requests.Session()
    sess.auth = HTTPDigestAuth(user, pwd)

    def recurse(a: dt.datetime, b: dt.datetime):
        sid  = str(uuid.uuid4())
        ok = dump_window(
            host, sess, sid,
            a.strftime("%Y-%m-%dT%H:%M:%SZ"),
            b.strftime("%Y-%m-%dT%H:%M:%SZ"),
            outfile, batch, verify_ssl,
        )
        if not ok:
            mid = a + (b - a) / 2
            recurse(a, mid)
            recurse(mid, b)

    recurse(start_dt, end_dt)


# ──────────────────────────────── CLI / main ─────────────────────────────────

def _parse_when(s: str, is_start: bool) -> dt.datetime:
    """Handle YYYY‑MM‑DD or full ISO; add 00:00/23:59 for plain date."""
    try:
        if len(s) == 10:      # yyyy-mm-dd
            base = dt.datetime.fromisoformat(s)
            if is_start:
                return base
            else:
                return base.replace(hour=23, minute=59, second=59)
        return dt.datetime.fromisoformat(s)
    except ValueError as e:
        print(f"⚠️  Invalid date/time '{s}': {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dump Hikvision log (raw XML)")
    ap.add_argument("host")
    ap.add_argument("user")
    ap.add_argument("start", help="start time (YYYY‑MM‑DD or ISO)")
    ap.add_argument("end",   help="end   time (YYYY‑MM‑DD or ISO, inclusive)")
    ap.add_argument("-o", "--out", default="hik_logs_raw.xml",
                    help="output file (default: %(default)s)")
    ap.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                    help="rows per page (default: %(default)s)")
    ap.add_argument("--insecure", action="store_true",
                    help="skip TLS certificate verification")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="HTTP debugging")
    args = ap.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    pwd = getpass.getpass(f"Password for {args.user}@{args.host}: ")

    start_dt = _parse_when(args.start, True)
    end_dt   = _parse_when(args.end,   False)
    if end_dt < start_dt:
        print("⚠️  END must be after START", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out).expanduser().resolve()
    print(f"⇣ Downloading raw XML to {out_path}")

    with out_path.open("wb") as fh:
        walk_time_range(
            host=args.host,
            user=args.user,
            pwd=pwd,
            start_dt=start_dt,
            end_dt=end_dt + dt.timedelta(seconds=1),  # make END inclusive
            outfile=fh,
            batch=args.batch,
            verify_ssl=not args.insecure,
        )

    print("✓ Done.")


if __name__ == "__main__":
    # mute warnings for self‑signed certs if --insecure is used
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
