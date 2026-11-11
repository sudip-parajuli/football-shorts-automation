"""Shared publication history with optimistic GitHub writes across workflows."""
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
import unicodedata

import requests

STOP_WORDS = set('a an the how why what who when is are was were do does did of for to in on at and or with from by this that shorts football soccer'.split())


class DuplicateContent(RuntimeError):
    pass


def normalized(text):
    text = unicodedata.normalize('NFKC', str(text)).casefold()
    return ' '.join(re.findall(r'\w+', text))


def body_text(text):
    text = re.split(r'\n\s*\n(?:sources?:|visual credits:|photo:|fixture data:)', str(text), maxsplit=1, flags=re.I)[0]
    text = re.sub(r'https?://\S+|#\w+', '', text)
    return normalized(text)


def media_identity(path):
    digest = hashlib.sha256()
    with open(path,'rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            digest.update(block)
    return 'video-' + digest.hexdigest()


def signature(topic, text=''):
    content = body_text(text)
    tokens = sorted(set(content.split()) - STOP_WORDS)
    return {'topic': topic, 'topic_words': sorted(set(normalized(topic).split()) - STOP_WORDS),
            'body_words': tokens, 'body_hash': hashlib.sha256(content.encode()).hexdigest() if content else ''}


def similar(candidate, prior):
    if candidate['body_hash'] and candidate['body_hash'] == prior.get('body_hash'):
        return True
    left, right = set(candidate['topic_words']), set(prior.get('topic_words', []))
    if left and left == right:
        return True
    numbers = lambda words: {word for word in words if word.isdigit()}
    changed_numbers = numbers(left) and numbers(right) and numbers(left) != numbers(right)
    if not changed_numbers and len(left & right) >= 4 and len(left & right) / len(left | right) >= .8:
        return True
    generic = {'match','preview','recap','premier','league','liga','bundesliga','serie','ligue','champions','mls','saudi','pro'}
    anchors = {word for word in left & right if not word.isdigit() and word not in generic}
    left, right = set(candidate['body_words']), set(prior.get('body_words', []))
    if numbers(left) and numbers(right) and numbers(left) != numbers(right):
        return False
    return len(anchors) >= 2 and len(left & right) >= 25 and len(left & right) / max(1, len(left | right)) >= .9


def seed_history():
    state = {'entries': {}, 'legacy_hashes': []}
    used = Path('footybitez/data/used_topics.json')
    if used.exists():
        for topic in json.loads(used.read_text(encoding='utf-8')):
            item = signature(topic)
            state['entries'][hashlib.sha256(normalized(topic).encode()).hexdigest()] = {**item, 'kind':'legacy', 'channels':{}}
    for name in ('general_news_state.json', 'news_state.json'):
        path = Path('footybitez/data') / name
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            state['legacy_hashes'].extend(data.get('processed_hashes', []))
    path = Path('footybitez/data/social_posts_state.json')
    if path.exists():
        for record in json.loads(path.read_text(encoding='utf-8')).values():
            plan = record.get('plan', {})
            if plan.get('topic') and (record.get('facebook') or record.get('instagram_id')):
                item = signature(plan['topic'], plan.get('caption', ''))
                state['entries']['post-'+plan['slot']] = {**item, 'kind':'legacy', 'channels':{}}
    return state


class ContentHistory:
    branch = 'content-history'
    filename = 'footybitez/data/content_history.json'

    def __init__(self, path=None):
        self.path = Path(path or self.filename)
        self.remote = os.getenv('GITHUB_ACTIONS') == 'true' and path is None
        self.repository = os.getenv('GITHUB_REPOSITORY', '')
        self.token = os.getenv('GITHUB_TOKEN', '')
        self.headers = {'Authorization':f'Bearer {self.token}', 'Accept':'application/vnd.github+json'}
        self.base = f'https://api.github.com/repos/{self.repository}'
        self._snapshot = None

    def _check(self, response):
        if not response.ok:
            raise RuntimeError(f'Publication history unavailable (GitHub HTTP {response.status_code})')

    def _read(self):
        if not self.remote:
            data = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else seed_history()
            return data, None
        if not self.token or not self.repository:
            raise RuntimeError('Publication history requires GITHUB_TOKEN and GITHUB_REPOSITORY in Actions')
        response = requests.get(f'{self.base}/contents/{self.filename}', params={'ref':self.branch}, headers=self.headers, timeout=25)
        if response.status_code == 404:
            return seed_history(), None
        self._check(response)
        payload = response.json()
        if payload.get('encoding') == 'none':
            raw_headers = {**self.headers, 'Accept':'application/vnd.github.raw+json'}
            raw = requests.get(f'{self.base}/contents/{self.filename}', params={'ref':self.branch}, headers=raw_headers, timeout=25)
            self._check(raw)
            return raw.json(), payload['sha']
        return json.loads(base64.b64decode(payload['content'])), payload['sha']

    def _ensure_branch(self):
        response = requests.get(f'{self.base}/git/ref/heads/{self.branch}', headers=self.headers, timeout=25)
        if response.status_code != 404:
            self._check(response)
            return
        main = requests.get(f'{self.base}/git/ref/heads/main', headers=self.headers, timeout=25)
        self._check(main)
        result = requests.post(f'{self.base}/git/refs', headers=self.headers,
            json={'ref':f'refs/heads/{self.branch}', 'sha':main.json()['object']['sha']}, timeout=25)
        if result.status_code in (409, 422):
            result = requests.get(f'{self.base}/git/ref/heads/{self.branch}', headers=self.headers, timeout=25)
        self._check(result)

    @contextmanager
    def _local_lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_suffix('.lock')
        for _ in range(50):
            try:
                descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                time.sleep(.1)
        else:
            raise RuntimeError('Publication history is locked by another process')
        try:
            os.close(descriptor)
            yield
        finally:
            lock.unlink(missing_ok=True)

    def _update(self, change):
        if not self.remote:
            with self._local_lock():
                data, _ = self._read()
                result = change(data)
                temporary = self.path.with_suffix('.tmp')
                temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
                temporary.replace(self.path)
                return result
        self._ensure_branch()
        for _ in range(4):
            data, sha = self._read()
            result = change(data)
            payload = {'message':'Update shared publication history [skip ci]', 'branch':self.branch,
                       'content':base64.b64encode(json.dumps(data,ensure_ascii=False).encode()).decode()}
            if sha:
                payload['sha'] = sha
            response = requests.put(f'{self.base}/contents/{self.filename}', headers=self.headers, json=payload, timeout=25)
            if response.status_code in (409, 422):
                continue
            self._check(response)
            return result
        raise RuntimeError('Publication history changed concurrently. Retry this run.')

    def is_duplicate(self, topic, text=''):
        candidate = signature(topic, text)
        if self._snapshot is None:
            self._snapshot, _ = self._read()
        data = self._snapshot
        raw_hash = hashlib.sha256(topic.encode()).hexdigest()
        return raw_hash in data.get('legacy_hashes', []) or any(similar(candidate, item) for item in data['entries'].values())

    def claim(self, topic, text, channel, resume=False, piece_id=None):
        candidate = signature(topic, text)
        key = piece_id or candidate['body_hash'] or hashlib.sha256(normalized(topic).encode()).hexdigest()
        kind = 'video' if channel in ('youtube','social') else 'post'

        def change(data):
            existing = data['entries'].get(key)
            if existing and existing.get('kind') == kind:
                publication = existing['channels'].get(channel)
                if publication:
                    if publication['status'] == 'published':
                        return {'key':key, 'previous':publication['result']}
                    if resume and channel == 'post':
                        return {'key':key, 'previous':None}
                    raise DuplicateContent(f'An earlier {channel} publishing outcome needs review for {topic}')
            else:
                if any(similar(candidate, item) for item in data['entries'].values()):
                    raise DuplicateContent(f'Topic or script has already been used: {topic}')
                existing = {**candidate, 'kind':kind, 'channels':{}}
                data['entries'][key] = existing
            existing['channels'][channel] = {'status':'pending', 'at':datetime.now(timezone.utc).isoformat()}
            return {'key':key, 'previous':None}
        return self._update(change)

    def complete(self, key, channel, result):
        def change(data):
            publication = data['entries'][key]['channels'][channel]
            publication.update(status='published', result=result)
        self._update(change)
