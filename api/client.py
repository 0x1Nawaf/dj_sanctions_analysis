import re
import sys
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from dj_sanctions.config import DJ_BASE_URL, DOWNLOAD_TIMEOUT, DOWNLOAD_CHUNK_SIZE


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for key, val in attrs:
                if key == "href" and val and not val.startswith(".."):
                    self.links.append(val)


def _dj_request(url, auth_b64):
    req = Request(url)
    req.add_header("Authorization", "Basic " + auth_b64)
    try:
        with urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            return resp.read()
    except HTTPError as e:
        print("HTTP Error %d: %s for %s" % (e.code, e.reason, url), file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print("Connection error: %s for %s" % (e.reason, url), file=sys.stderr)
        sys.exit(1)


def list_remote_files(auth_b64):
    print("Listing files at %s ..." % DJ_BASE_URL)
    body = _dj_request(DJ_BASE_URL, auth_b64).decode("utf-8", errors="replace")

    parser = _LinkParser()
    parser.feed(body)
    files = [f for f in parser.links if f.strip()]

    if not files:
        for token in re.split(r'[,\s\n]+', body):
            token = token.strip()
            if token and (".zip" in token or ".xml" in token):
                files.append(token)

    expanded = []
    for f in files:
        for part in f.split(","):
            part = part.strip()
            if part:
                expanded.append(part)

    return sorted(expanded)


def download_file(filename, auth_b64):
    url = DJ_BASE_URL + filename
    print("Downloading %s ..." % url)

    req = Request(url)
    req.add_header("Authorization", "Basic " + auth_b64)

    try:
        resp = urlopen(req, timeout=DOWNLOAD_TIMEOUT)
    except HTTPError as e:
        print("  HTTP Error %d: %s" % (e.code, e.reason), file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print("  Connection error: %s" % e.reason, file=sys.stderr)
        sys.exit(1)

    total = resp.headers.get("Content-Length")
    total = int(total) if total else None

    chunks = []
    downloaded = 0
    while True:
        chunk = resp.read(DOWNLOAD_CHUNK_SIZE)
        if not chunk:
            break
        chunks.append(chunk)
        downloaded += len(chunk)
        mb = downloaded / (1024 * 1024)
        if total:
            pct = downloaded * 100 / total
            total_mb = total / (1024 * 1024)
            sys.stdout.write("\r  %.1f / %.1f MB (%.0f%%)" % (mb, total_mb, pct))
        else:
            sys.stdout.write("\r  %.1f MB downloaded ..." % mb)
        sys.stdout.flush()

    resp.close()
    print()

    data = b"".join(chunks)
    print("  Download complete: %.1f MB" % (len(data) / (1024 * 1024)))
    return data


def classify_files(files):
    result = {"full": [], "daily": [], "incremental": []}
    for f in files:
        fl = f.lower()
        if "pfa2" not in fl:
            continue
        if "_splits" in fl:
            continue
        if "_f." in fl:
            result["full"].append(f)
        elif "_i." in fl:
            result["incremental"].append(f)
        elif "_d." in fl:
            result["daily"].append(f)
    for k in result:
        result[k] = sorted(result[k])
    return result


def extract_date_from_filename(filename):
    m = re.search(r'(\d{12})', filename)
    return m.group(1) if m else ""
