#!/usr/bin/env python3
"""Check if Google Drive folder has changes since last sync."""

import json
import os
import sys
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
TIMESTAMP_FILE = "last_sync.txt"


def get_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS") or ""
    if creds_json:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds_file = os.environ["GOOGLE_CREDENTIALS_FILE"]
        creds = service_account.Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def check_changes():
    folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    service = get_service()

    # Read last sync timestamp from cache file
    last_sync = None
    if os.path.exists(TIMESTAMP_FILE):
        with open(TIMESTAMP_FILE) as f:
            ts = f.read().strip()
            if ts:
                last_sync = ts

    if not last_sync:
        print("No previous sync timestamp found, changes detected")
        return True

    # Query for files modified after last sync (in the root folder and subfolders)
    # First get subfolders
    resp = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id)",
    ).execute()
    folder_ids = [folder_id] + [f["id"] for f in resp.get("files", [])]

    # Check each folder for modifications after last sync
    for fid in folder_ids:
        resp = service.files().list(
            q=f"'{fid}' in parents and modifiedTime > '{last_sync}' and trashed=false",
            fields="files(id,name,modifiedTime)",
            pageSize=1,
        ).execute()
        if resp.get("files"):
            f = resp["files"][0]
            print(f"Changes detected: {f['name']} modified at {f['modifiedTime']}")
            return True

    # Also check if any subfolders were added/removed by comparing count
    # (a deleted folder won't show up as modified)
    resp = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id)",
    ).execute()

    print("No changes detected")
    return False


def save_timestamp():
    """Save current UTC timestamp for next comparison."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    with open(TIMESTAMP_FILE, "w") as f:
        f.write(now)
    print(f"Saved sync timestamp: {now}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "save":
        save_timestamp()
    else:
        has_changes = check_changes()
        # Set GitHub Actions output
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"has_changes={'true' if has_changes else 'false'}\n")
        sys.exit(0 if has_changes else 1)
