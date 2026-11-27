"""Browser-local completed notes. No archive database or API keys."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import uuid
import streamlit as st
from engine import render_note


def completed_record(state):
    """Only explicitly selected note fields may reach browser storage."""
    payload={'items':state['items'],'info':state['info']}
    fingerprint=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if state.get('_archive_fingerprint')!=fingerprint:
        now=datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
        record_id=state.setdefault('_archive_note_id',str(uuid.uuid4()))
        previous=state.get('_archive_record',{})
        info=state['info']
        title=' · '.join(str(info.get(k,'')) for k in ('회사','직무') if info.get(k)) or '면접 복기'
        state['_archive_record']={
            'id':record_id,'title':title,'createdAt':previous.get('createdAt',now),
            'updatedAt':now,'note':render_note(state['items'],info,state['memo']),
        }
        state['_archive_fingerprint']=fingerprint
    return state['_archive_record']


_component=st.components.v2.component(
    'memento_browser_archive_v1',
    html='<div class="storage-status" role="status"></div><section class="archive" hidden><input class="search" type="search" aria-label="보관함 검색" placeholder="회사, 직무 또는 내용 검색"><p class="count"></p><div class="list"></div><div class="detail"></div></section>',
    css='''
    :host{font-family:inherit;color:#22374b}*{box-sizing:border-box}
    .storage-status{font-size:14px;line-height:1.7;color:#526d85;margin-bottom:12px}
    .storage-status.error{color:#a13c32;background:#fff0ec;padding:14px;border-radius:12px}
    .search{width:100%;font:inherit;font-size:16px;border:1px solid #bbccdb;background:white;color:#22374b;padding:13px 15px;border-radius:12px}
    .count,.meta,.empty{font-size:14px;color:#64798e;line-height:1.7}
    .card{border-bottom:1px solid #d9e3eb;padding:20px 0}
    h3{font-size:18px;font-weight:650;margin:0 0 6px;line-height:1.5}
    button{font:inherit;font-size:14px;border:1px solid #bbccdb;background:white;color:#22374b;border-radius:999px;padding:9px 16px;cursor:pointer;margin:8px 8px 0 0}
    button:hover{background:#dbeeff}button.primary{background:#90a3b4;border-color:#90a3b4}button.danger{color:#a13c32}
    button:focus-visible,input:focus-visible{outline:2px solid #526f8c;outline-offset:3px}
    .preview{font-size:15px;line-height:1.8;white-space:pre-wrap;margin:20px 0;padding:20px;background:#f5f9fc;border-radius:14px;overflow-wrap:anywhere;max-height:650px;overflow:auto}
    .detail{padding-top:20px}.detail:empty{display:none}
    ''',
    js=(Path(__file__).parent/'assets'/'archive.js').read_text(),
)


def mount_archive(record=None,show=False):
    return _component(data={'record':record,'show':show},key='browser_archive',height='content')
