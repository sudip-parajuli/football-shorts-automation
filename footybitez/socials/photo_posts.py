"""Facebook photo/text and Instagram photo publishing with per-platform results."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import requests
from footybitez.socials.meta_publisher import MetaPublisher


class MetaRejected(RuntimeError):
    """A definite API rejection, unlike an ambiguous network timeout."""


def failure_message(error):
    return type(error).__name__ if isinstance(error, requests.RequestException) else str(error)


def host_post_image(image_path):
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not repo or not token or os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Instagram image hosting requires GitHub Actions or PUBLIC_POST_IMAGE_URL")
    source = Path(image_path).resolve()
    filename = "photo-" + hashlib.sha256(source.read_bytes()).hexdigest()[:20] + ".jpg"
    with tempfile.TemporaryDirectory(prefix="footybitez-photo-") as directory:
        def run(args):
            result = subprocess.run(["git", *args], cwd=directory, capture_output=True)
            if result.returncode:
                # Never include a credential-bearing command or subprocess text.
                raise RuntimeError("Public image hosting failed")
        run(["init", "--initial-branch=temp-photo-host"])
        run(["config", "user.name", "github-actions[bot]"])
        run(["config", "user.email", "github-actions[bot]@users.noreply.github.com"])
        shutil.copy2(source, Path(directory) / filename)
        run(["add", filename])
        run(["commit", "-m", "Host social post image"])
        run(["push", f"https://x-access-token:{token}@github.com/{repo}.git", "temp-photo-host", "--force"])
    return f"https://raw.githubusercontent.com/{repo}/temp-photo-host/{filename}"


class PhotoPostPublisher:
    def __init__(self, use_footybitez=True):
        self.meta = MetaPublisher(use_footybitez=use_footybitez)
        if use_footybitez:
            # The photo workflow belongs to FootyBitez. Never combine its token
            # with generic account IDs or silently publish to a different brand.
            self.meta.access_token = os.getenv('FOOTYBITEZ_META_ACCESS_TOKEN')
            self.meta.page_id = os.getenv('FOOTYBITEZ_FACEBOOK_PAGE_ID')
            self.meta.page_ids_filter = os.getenv('FOOTYBITEZ_FACEBOOK_PAGE_IDS')
            self.meta.instagram_id = os.getenv('FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID')
        self.use_footybitez = use_footybitez
        self.version = os.getenv("META_GRAPH_API_VERSION", "v26.0")
        self.meta.api_version = self.version
        self.base = f"https://graph.facebook.com/{self.version}"

    @staticmethod
    def _response_id(response):
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(f"Meta returned non-JSON response (HTTP {response.status_code})")
        if not response.ok or not data.get("id"):
            error = data.get("error", {})
            raise MetaRejected(f"Meta publishing failed (HTTP {response.status_code}, code={error.get('code')}, subcode={error.get('error_subcode')})")
        return str(data["id"])

    def pages(self):
        if self.use_footybitez and (not self.meta.access_token or not (self.meta.page_id or self.meta.page_ids_filter)):
            raise RuntimeError('Configure FOOTYBITEZ_META_ACCESS_TOKEN and FOOTYBITEZ_FACEBOOK_PAGE_ID (or FOOTYBITEZ_FACEBOOK_PAGE_IDS)')
        pages = self.meta._get_authorized_pages()
        targets = [value.strip() for value in (self.meta.page_ids_filter or self.meta.page_id or "").split(',') if value.strip()]
        if targets:
            pages = [page for page in pages if page.get("id") in targets]
        if not pages and self.meta.page_id and self.meta.access_token:
            pages = [{"id":self.meta.page_id,"access_token":self.meta.access_token}]
        if not pages:
            raise RuntimeError("No configured Facebook Page is available")
        return pages

    def facebook(self, page, caption, image_path=None):
        token = page.get("access_token") or self.meta.access_token
        if not token:
            raise RuntimeError("Facebook page token is missing")
        endpoint = "photos" if image_path else "feed"
        payload = {"access_token":token,"message":caption}
        if image_path:
            with open(image_path, "rb") as image:
                response = requests.post(f"{self.base}/{page['id']}/{endpoint}", data=payload,
                                         files={"source":image}, timeout=90)
        else:
            response = requests.post(f"{self.base}/{page['id']}/{endpoint}", data=payload, timeout=30)
        return self._response_id(response)

    def instagram(self, image_path, caption, record, save):
        if not self.meta.instagram_id or not self.meta.access_token:
            raise RuntimeError("FootyBitez Instagram requires FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID and FOOTYBITEZ_META_ACCESS_TOKEN" if self.use_footybitez else "Instagram account/token is missing")
        # An ambiguous publish response is not automatically retried: doing so can
        # create a duplicate even if the original request succeeded on Meta.
        if record.get("instagram_publish_pending"):
            raise RuntimeError("Instagram publish outcome needs review; check the account before resetting pending state")
        creation_id = record.get("instagram_container_id")
        if not creation_id:
            response = requests.get(f"{self.base}/{self.meta.instagram_id}", params={"fields":"id","access_token":self.meta.access_token}, timeout=20)
            self._response_id(response)
            public_url = os.getenv("PUBLIC_POST_IMAGE_URL") or host_post_image(image_path)
            # Check public availability before handing the URL to Meta.
            for attempt in range(6):
                check = requests.get(public_url, stream=True, timeout=20)
                ready = check.ok and check.headers.get("Content-Type", "").startswith("image/")
                check.close()
                if ready:
                    break
                time.sleep(2)
            else:
                raise RuntimeError("Hosted image is not publicly available yet")
            response = requests.post(f"{self.base}/{self.meta.instagram_id}/media",
                data={"image_url":public_url,"caption":caption[:2200],"access_token":self.meta.access_token}, timeout=40)
            creation_id = self._response_id(response)
            record["instagram_container_id"] = creation_id
            save()
        for _ in range(18):
            response = requests.get(f"{self.base}/{creation_id}", params={"fields":"status_code","access_token":self.meta.access_token}, timeout=20)
            status = response.json().get("status_code") if response.ok else "ERROR"
            if status in ("FINISHED", "PUBLISHED"):
                break
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram image processing failed ({status})")
            time.sleep(3)
        else:
            raise RuntimeError("Instagram image processing timed out")
        record["instagram_publish_pending"] = True
        save()
        response = requests.post(f"{self.base}/{self.meta.instagram_id}/media_publish",
            data={"creation_id":creation_id,"access_token":self.meta.access_token}, timeout=40)
        try:
            media_id = self._response_id(response)
        except MetaRejected:
            record.pop('instagram_publish_pending',None)
            save()
            raise
        record["instagram_id"] = media_id
        record.pop("instagram_publish_pending", None)
        save()
        return media_id


def publish_post(plan, state, state_path, publisher=None):
    history = None
    claim = None
    if publisher is None:
        from footybitez.content.history import ContentHistory
        history = ContentHistory()
        claim = history.claim(plan['topic'], plan['caption'], 'post', resume=plan['slot'] in state)
        if claim['previous'] is not None:
            return claim['previous']
    publisher = publisher or PhotoPostPublisher()
    record = state.setdefault(plan["slot"], {"plan":plan,"facebook":{}})
    def save():
        path = Path(state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state,indent=2),encoding="utf-8")
        temporary.replace(path)
    save()
    failures = []
    try:
        pages = publisher.pages()
        for page in pages:
            pid = str(page["id"])
            if record.get("facebook", {}).get(pid):
                continue
            pending = record.setdefault("facebook_pending", {})
            if pending.get(pid):
                failures.append(f"Facebook {pid} publish outcome needs review")
                continue
            pending[pid] = True
            save()
            try:
                post_id = publisher.facebook(page, plan["caption"], plan.get("image_path") if plan["format"]=="photo" else None)
                record.setdefault("facebook", {})[pid] = post_id
                pending.pop(pid,None)
                save()
            except Exception as error:
                if isinstance(error, MetaRejected):
                    pending.pop(pid,None)
                    save()
                # Preserve pending: a timeout can conceal a successful publish.
                failures.append(failure_message(error))
    except Exception as error:
        failures.append(failure_message(error))
    if plan["format"] == "photo" and not record.get("instagram_id"):
        try:
            publisher.instagram(plan["image_path"],plan["caption"],record,save)
        except Exception as error:
            failures.append(failure_message(error))
    if plan["format"] == "text":
        record["instagram_skipped"] = "Facebook text-only post; Instagram requires an image"
    save()
    if failures:
        raise RuntimeError("; ".join(failures))
    if history is not None:
        history.complete(claim['key'], 'post', {'facebook':record.get('facebook',{}),'instagram_id':record.get('instagram_id')})
    return record
