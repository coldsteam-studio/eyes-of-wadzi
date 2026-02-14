#!/usr/bin/env python3
"""Download images from Google Drive and generate Hugo gallery content."""

import io
import json
import os
import shutil
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "galleries"
IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/tiff"}


def get_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS") or ""
    if creds_json:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        creds_file = os.environ["GOOGLE_CREDENTIALS_FILE"]
        creds = service_account.Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def list_subfolders(service, parent_id):
    resp = service.files().list(
        q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name,description,createdTime)",
        orderBy="name",
    ).execute()
    return resp.get("files", [])


def list_images(service, folder_id):
    resp = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,description,mimeType,createdTime)",
        orderBy="name",
    ).execute()
    files = resp.get("files", [])
    images = [f for f in files if f["mimeType"] in IMAGE_MIMETYPES]
    skipped = [f for f in files if f["mimeType"] not in IMAGE_MIMETYPES]
    for f in skipped:
        print(f"    Skipped: {f['name']} (mimeType: {f['mimeType']})")
    return images


def download_file(service, file_id, dest_path):
    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def yaml_escape(s):
    if any(c in s for c in ':{}[],"\'#&*!|>%@`'):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def generate_index_md(title, date, resources, body=""):
    lines = ["---"]
    lines.append(f"title: {yaml_escape(title)}")
    lines.append(f"date: {date}")
    if resources:
        lines.append("resources:")
        for res in resources:
            lines.append(f"  - src: {res['src']}")
            if res.get("title"):
                lines.append(f"    title: {yaml_escape(res['title'])}")
    lines.append("---")
    if body:
        lines.append("")
        lines.append(body.strip())
    lines.append("")
    return "\n".join(lines)


def sync():
    folder_id = os.environ["GOOGLE_DRIVE_FOLDER_ID"]
    service = get_service()

    # Clean and recreate content directory
    if CONTENT_DIR.exists():
        shutil.rmtree(CONTENT_DIR)
    CONTENT_DIR.mkdir(parents=True)

    # Generate _index.md for the galleries list page
    index_content = "---\ntitle: Galleries\n---\n"
    (CONTENT_DIR / "_index.md").write_text(index_content)

    subfolders = list_subfolders(service, folder_id)
    print(f"Found {len(subfolders)} galleries")

    for folder in subfolders:
        name = folder["name"]
        gallery_dir = CONTENT_DIR / name
        gallery_dir.mkdir()

        images = list_images(service, folder["id"])
        print(f"  {name}: {len(images)} images")

        # Download images
        resources = []
        for img in images:
            # Sanitize filename: lowercase, replace spaces with hyphens
            safe_name = img["name"].lower().replace(" ", "-")
            dest = gallery_dir / safe_name
            download_file(service, img["id"], dest)
            size_kb = dest.stat().st_size / 1024
            print(f"    Downloaded: {img['name']} -> {safe_name} ({size_kb:.0f} KB)")
            res = {"src": safe_name}
            if img.get("description"):
                res["title"] = img["description"]
            resources.append(res)

        # Use folder creation date or today
        date = folder.get("createdTime", "")[:10] or "2026-02-14"
        title = name.replace("-", " ").title()
        body = folder.get("description", "") or ""

        index_md = generate_index_md(title, date, resources, body)
        (gallery_dir / "index.md").write_text(index_md)
        print(f"  {name}: index.md generated")

    print("Sync complete")


if __name__ == "__main__":
    sync()
