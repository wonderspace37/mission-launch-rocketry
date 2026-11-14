#!/usr/bin/env python3
"""Export Onshape documents to STEP so the CAD lives in git next to the OpenRocket files.

Every Part Studio and Assembly in each document becomes one STEP file (millimetres):

    <out>/<document>/<tab>.step

A `manifest.json` next to them records where each file came from (document, workspace, tab, who last changed the
document and when, and when it was exported), so a STEP in the repo can always be traced back to the Onshape state it
was taken from. Onshape keeps its own full history; the repo keeps snapshots.

Keys: set ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY (Onshape > My account > Developer > API keys, read-only is enough),
or keep them in ~/.config/onshape/credentials.json as {"access_key": ..., "secret_key": ...}.
Free and Education plans get 2,500 API calls a year. One tab costs about 4-6 calls; --dry-run shows what would export.

Usage:
    python3 tools/onshape_export.py --folder f2d18b15de37473e3bdf9cea --out yellow-jacket/cad/onshape
    python3 tools/onshape_export.py --doc 403251906b89431bd729f945 --out yellow-jacket/cad/onshape
"""
import argparse
import base64
import datetime as dt
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import string
import sys
import time
import zipfile
from email.utils import formatdate
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests

BASE = "https://cad.onshape.com"
API = "v10"
LEDGER = Path.home() / ".config/onshape/usage.jsonl"   # same ledger the onshape-cad toolkit uses, if present


class Onshape:
    def __init__(self):
        ak, sk = os.environ.get("ONSHAPE_ACCESS_KEY"), os.environ.get("ONSHAPE_SECRET_KEY")
        if not (ak and sk):
            creds = Path.home() / ".config/onshape/credentials.json"
            if not creds.exists():
                sys.exit("No Onshape keys: set ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY.")
            c = json.loads(creds.read_text())
            ak, sk = c["access_key"], c["secret_key"]
        self.ak, self.sk = ak, sk
        self.s = requests.Session()
        self.calls = 0

    def _headers(self, method, url, ctype, accept):
        nonce = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(25))
        date = formatdate(usegmt=True)
        u = urlparse(url)
        msg = f"{method}\n{nonce}\n{date}\n{ctype}\n{u.path}\n{u.query}\n".lower()
        sig = base64.b64encode(hmac.new(self.sk.encode(), msg.encode(), hashlib.sha256).digest()).decode()
        return {"Date": date, "On-Nonce": nonce, "Content-Type": ctype, "Accept": accept,
                "Authorization": f"On {self.ak}:HmacSHA256:{sig}"}

    def call(self, method, path, params=None, body=None, raw=False):
        url = path if path.startswith("http") else f"{BASE}/api/{API}{path}"
        if params:
            url += "?" + urlencode(params)
        accept = "application/octet-stream" if raw else "application/json;charset=UTF-8; qs=0.09"
        data = json.dumps(body) if body is not None else None
        for _ in range(6):
            r = self.s.request(method, url, headers=self._headers(method, url, "application/json", accept), data=data,
                               allow_redirects=False, timeout=300)
            if 200 <= r.status_code < 400:
                self.calls += 1
                if LEDGER.parent.exists():
                    with open(LEDGER, "a") as f:
                        f.write(json.dumps({"t": dt.datetime.now().isoformat(timespec="seconds"), "m": method,
                                            "p": urlparse(url).path, "s": r.status_code}) + "\n")
            if r.status_code in (301, 302, 303, 307, 308):
                loc = r.headers["Location"]
                url = loc if loc.startswith("http") else BASE + loc
                if r.status_code == 303:
                    method, data = "GET", None
                continue
            if r.status_code == 429:
                time.sleep(min(float(r.headers.get("Retry-After", 5)), 60))
                continue
            break
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {urlparse(url).path} -> HTTP {r.status_code}: {r.text[:500]}")
        return r.content if raw else (r.json() if r.content else None)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "untitled"


def export_tab(api, did, wid, el, dest):
    kind = "partstudios" if el["elementType"] == "PARTSTUDIO" else "assemblies"
    try:
        req = api.call("POST", f"/{kind}/d/{did}/w/{wid}/e/{el['id']}/export/step",
                       body={"stepUnit": "MILLIMETER", "storeInDocument": False, "notifyUser": False,
                             "triggerAutoDownload": False, "destinationName": el["name"]})
    except RuntimeError as e:  # e.g. "No visible parts to export" for an empty tab
        msg = str(e)
        return None, (msg.split('"message" : "')[1].split('"')[0] if '"message" : "' in msg else msg[:200])
    tid, state, wait = req["id"], req.get("requestState"), 3.0
    for _ in range(20):
        if state in ("DONE", "FAILED"):
            break
        time.sleep(wait)
        wait = min(wait * 1.5, 15)
        req = api.call("GET", f"/translations/{tid}")
        state = req.get("requestState")
    if state != "DONE":
        return None, req.get("failureReason") or state
    blob = api.call("GET", f"/documents/d/{did}/externaldata/{req['resultExternalDataIds'][0]}", raw=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    return unpack(blob, dest), None


def unpack(blob, dest):
    """Onshape sends a zip with one STEP per part when a tab has several parts. Write <tab>--<part>.step for each."""
    if blob[:2] != b"PK":
        dest.write_bytes(blob)
        return [dest.name]
    names = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for m in z.namelist():
            if not m.lower().endswith((".step", ".stp")):
                continue
            part = slug(Path(m).stem.split(" - ", 1)[-1])
            out = dest.with_name(f"{dest.stem}--{part}.step")
            out.write_bytes(z.read(m))
            names.append(out.name)
    return names


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--folder", action="append", default=[], help="Onshape folder id (exports every document in it)")
    p.add_argument("--doc", action="append", default=[], help="Onshape document id")
    p.add_argument("--out", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    api = Onshape()
    out = Path(a.out)
    dids = list(a.doc)
    for fid in a.folder:
        r = api.call("GET", f"/globaltreenodes/folder/{fid}", {"limit": 20})
        while True:
            dids += [it["id"] for it in r.get("items", []) if it.get("jsonType") == "document-summary"]
            if not r.get("next"):
                break
            r = api.call("GET", r["next"])

    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for did in dict.fromkeys(dids):
        d = api.call("GET", f"/documents/{did}")
        wid = d["defaultWorkspace"]["id"]
        els = [e for e in api.call("GET", f"/documents/d/{did}/w/{wid}/elements")
               if e["elementType"] in ("PARTSTUDIO", "ASSEMBLY")]
        folder = out / slug(d["name"] if not d.get("trash") else d["name"])
        # documents that share a name (three "Upper Stage"s) get the short id appended
        same = [k for k, v in manifest.items() if v["folder"] == folder.name and k != did]
        if same:
            folder = out / f"{slug(d['name'])}-{did[:6]}"
        print(f"{d['name']}  ({did}, modified {d['modifiedAt'][:10]} by {d['modifiedBy']['name']}"
              f"{', in trash' if d.get('trash') else ''}{', private' if not d.get('public') else ''})")
        entry = {"name": d["name"], "folder": folder.name, "url": f"{BASE}/documents/{did}/w/{wid}",
                 "public": d.get("public"), "owner": d["owner"]["name"], "created_by": d["createdBy"]["name"],
                 "modified_at": d["modifiedAt"], "modified_by": d["modifiedBy"]["name"], "tabs": []}
        used = set()
        for el in els:
            fname = slug(el["name"])
            if fname in used:
                fname = f"{fname}-{el['id'][:6]}"
            used.add(fname)
            dest = folder / f"{fname}.step"
            if a.dry_run:
                print(f"   would export {el['elementType'].lower()} '{el['name']}' -> {dest}")
                continue
            files, err = export_tab(api, did, wid, el, dest)
            print(f"   {el['elementType'].lower():<10s} {el['name']:<28s} -> " +
                  (", ".join(str(folder / f) for f in files) if files else f"FAILED: {err}"))
            entry["tabs"].append({"name": el["name"], "type": el["elementType"], "element_id": el["id"],
                                  "files": files or [], "error": err,
                                  "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
        manifest[did] = entry
    if not a.dry_run:
        out.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"\n{api.calls} Onshape API calls")


if __name__ == "__main__":
    main()
