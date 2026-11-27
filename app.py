import hmac
import os
import re
import streamlit as st
from engine import KINDS, STATUSES, QUESTIONS, NOTICE, extract, candidate, choose_question, render_note, ask_api

st.set_page_config(page_title='MEMENTŌ · 면접 복기', page_icon='🌿', layout='centered')
from ui import apply_style, memory_card, summary_metrics
from home import neuron_home
from archive import completed_record, mount_archive
apply_style()

def setting(key,default=''):
    try:
        return st.secrets.get(key,os.environ.get(key,default))
    except FileNotFoundError:
        return os.environ.get(key,default)


def reset():
    auth=st.session_state.get('authenticated',False)
    for k in list(st.session_state):
        del st.session_state[k]
    st.session_state.authenticated=auth


def open_archive():
    st.session_state.show_archive=True
    st.session_state.show_home=False


st.markdown('''<style>
.stAppDeployButton,[data-testid="stAppDeployButton"] {display:none!important}
.st-key-top_archive {position:fixed!important;top:8px;right:48px;width:108px!important;z-index:1000002}
.st-key-top_archive button {min-height:36px!important;padding:6px 8px!important;border:0!important;background:transparent!important;border-radius:8px!important;font-size:14px!important;color:#22374B!important}
.st-key-top_archive button:hover {background:#DBEEFF!important}
.st-key-top_archive button:focus-visible {outline:2px solid #90A3B4!important;outline-offset:2px}
</style>''',unsafe_allow_html=True)
st.button('복기보관함',key='top_archive',type='tertiary',on_click=open_archive)


if st.session_state.get('authenticated'):
    st.markdown('<div class="brand">memento<span>MEMORY REPLAY</span></div>',unsafe_allow_html=True)
if st.session_state.get('authenticated') and st.session_state.get('stage',0)==0 and not st.session_state.get('show_archive') and not st.session_state.get('show_home'):
    st.caption('기억을 되짚고, 확인하고, 기록하는')
    st.title('기억을 되짚고, 나의 기록으로.')
    st.markdown('면접이 끝난 직후의 기억을 차분히 정리하세요. 빈 기억을 추측하지 않고, 직접 확인한 만큼 기록합니다.')

if not st.session_state.get('authenticated'):
    st.markdown('''<style>
    .block-container {max-width:none!important;padding:0 0 2rem!important}
    [data-testid="stHeader"] {background:transparent}
    iframe {border:none!important;outline:none!important;box-shadow:none!important;display:block}
    [data-testid="stForm"] {max-width:520px;margin:0 auto;padding:0 24px!important;border:none!important;background:transparent}
    [data-testid="stCaptionContainer"] {text-align:center;padding:0 20px}
    </style>''',unsafe_allow_html=True)
    neuron_home()
    st.caption('AI 면접 복기 · 비밀번호를 입력하면 나의 기록을 시작할 수 있어요.')
    with st.form('login',clear_on_submit=True):
        password=st.text_input('접속 비밀번호',type='password')
        submit=st.form_submit_button('메멘토 시작하기',type='primary',use_container_width=True)
    if submit:
        if hmac.compare_digest(password.encode(),str(setting('APP_PASSWORD','pnumis')).encode()):
            st.session_state.authenticated=True
            st.session_state.pop('password',None)
            st.rerun()
        else:
            st.error('비밀번호를 확인해 주세요.')
    st.caption('면접 직후의 메모에서 시작하는 대화형 복기 서비스')
    st.stop()

for k,v in {'stage':0,'items':[],'memo':'','info':{},'messages':[],'used':[],'current_question':None,'misses':0,'calls':0,'verify_summary':False}.items():
    if k not in st.session_state:
        st.session_state[k]=v
s=st.session_state
with st.sidebar:
    st.subheader('나만의 복기 공간')
    mode=st.radio('진행 방식',['Gemini 연결','기본 모드','OpenAI 연결'],help='Gemini를 연결하거나, API 없이 기본 모드를 사용할 수 있어요.')
    provider='gemini' if mode=='Gemini 연결' else 'openai'
    service='Gemini' if provider=='gemini' else 'OpenAI'
    key=''
    model=''
    consent=False
    if mode!='기본 모드':
        prefix='GEMINI' if provider=='gemini' else 'OPENAI'
        stored=setting(prefix+'_API_KEY')
        if stored:
            st.caption('서버에 설정된 API 키를 사용합니다.')
            key=stored
        else:
            key=st.text_input(service+' API 키',type='password',key=provider+'_api_key',help='현재 세션에서만 사용합니다. 새 복기 시작이나 로그아웃 시 지워집니다.')
        default_model='gemini-3.5-flash-lite' if provider=='gemini' else 'gpt-4.1-mini'
        model=st.text_input('모델 이름',value=setting(prefix+'_MODEL',default_model),key=provider+'_model')
        if provider=='gemini':
            st.caption('무료 티어로 설정된 프로젝트와 무료 지원 모델을 사용해 주세요. 이 앱은 계정의 과금 상태를 변경하지 않습니다.')
            if st.button('Gemini 연결 확인',disabled=not key.strip() or s.calls>=12,use_container_width=True):
                s.calls+=1
                try:
                    with st.spinner('Gemini 연결을 확인하고 있어요…'):
                        result=ask_api(key,model,'Return JSON with status equal to ok.',{'message':'connection test'},
                            {'type':'object','properties':{'status':{'type':'string','enum':['ok']}},'required':['status'],'additionalProperties':False},provider='gemini')
                    if result.get('status')=='ok':
                        st.success('Gemini 연결에 성공했어요.')
                    else:
                        st.error('응답 형식을 확인하지 못했어요. 다시 시도해 주세요.')
                except RuntimeError as e:
                    st.error(str(e))
            st.caption('연결 확인에는 예시 문장만 전송해요. 메모는 보내지 않습니다.')
        consent=st.checkbox('메모와 확인한 기억을 '+service+' API로 전송하는 데 동의해요.',key=provider+'_consent')
    enabled=bool(mode!='기본 모드' and key.strip() and model.strip() and consent and s.calls<12)
    st.caption(service+' 연결 준비됨' if enabled else '현재 기본 모드로 진행합니다.')
    if mode!='기본 모드' and not enabled:
        st.info('API 키와 전송 동의를 확인해 주세요. 세션당 최대 12회 요청할 수 있어요.')
    st.divider()
    st.caption('기억나지 않으면 건너뛰어도 괜찮아요. AI는 기억의 진위를 판정하지 않습니다.')
    st.caption('완성한 노트는 같은 브라우저의 보관함에 자동으로 남아요. API 키는 저장하지 않습니다.')
    if st.button('홈 화면 보기',use_container_width=True):
        s.show_archive=False
        s.show_home=True
        st.rerun()
    st.button('새 복기 시작',on_click=reset,use_container_width=True)
    if st.button('로그아웃',use_container_width=True):
        reset()
        s.authenticated=False
        st.rerun()

if s.get('show_archive'):
    st.subheader('내 복기 보관함')
    st.caption('이 브라우저에 자동 보관된 완성 노트예요. 다른 브라우저나 기기에는 공유되지 않아요.')
record=completed_record(s) if s.stage==4 else None
mount_archive(record=record,show=bool(s.get('show_archive')))
if s.get('show_archive'):
    if st.button('진행 중인 복기로 돌아가기'):
        s.show_archive=False;st.rerun()
    st.stop()

if s.get('show_home'):
    st.title('기억이 연결되는 순간.')
    st.write('흩어진 장면을 되짚고, 직접 확인한 기억을 나의 기록으로 남겨요.')
    neuron_home()
    if st.button('복기 이어가기',type='primary'):
        s.show_home=False;st.rerun()
    st.stop()

labels=['빠른 메모','기억 확인','대화형 복기','최종 검토','복기 노트']
st.progress((s.stage+1)/5,text=f'{s.stage+1} / 5 · {labels[s.stage]}')

def ai_extract(text):
    if enabled:
        s.calls+=1
    try:
        with st.spinner('메모를 기억 항목으로 나누고 있어요…'):
            return extract(text,key if enabled else '',model,provider=provider)
    except RuntimeError as e:
        st.error(str(e))
        st.info('입력은 보존했어요. 왼쪽에서 기본 모드로 바꾼 뒤 다시 눌러 주세요.')
        return None


def next_question():
    if s.misses>=2 or len(s.used)>=len(QUESTIONS):
        s.current_question=None
        return
    if enabled:
        s.calls+=1
    try:
        q=choose_question(s['items'],s.used,key if enabled else '',model,provider=provider)
    except RuntimeError:
        q=choose_question(s['items'],s.used)
        s.messages.append({'role':'assistant','content':'AI 연결이 원활하지 않아 기본 질문으로 이어갈게요.'})
    s.current_question=q
    if q is not None:
        s.used.append(q)
        s.messages.append({'role':'assistant','content':QUESTIONS[q]})


def review_items(prefix):
    done=sum(i['status']!='미확인' for i in s['items'])
    st.caption(f"{done} / {len(s['items'])}개 확인 · 원문과 비교하며 확인해 주세요")
    for idx,item in enumerate(s['items']):
        memory_card(item,idx,prefix,allow_order=prefix=='final')
    st.caption('‘맞아요’는 AI의 이해가 내 기억과 맞다는 뜻이에요. 사건의 객관적 사실을 판정하는 단계가 아닙니다.')

if s.stage==0:
    st.subheader('떠오르는 것부터, 빠르게.')
    st.caption('순서가 뒤섞여도, 완전한 문장이 아니어도 괜찮아요. 항목마다 줄을 바꾸면 확인하기 편해요.')
    if st.button('예시 메모 불러오기'):
        s.memo_input='자기소개를 했다.\n프로젝트에서 내가 맡은 역할을 물어봤다.\nAI 활용 경험 질문도 있었던 것 같다.\n질문의 순서는 잘 모르겠다.\n긴장해서 말이 조금 빨라진 느낌이다.'
    with st.form('memo_form'):
        memo=st.text_area('면접 직후 메모',key='memo_input',height=210,max_chars=8000,placeholder='기억나는 질문, 내가 한 답변, 떠오르는 장면…')
        submit=st.form_submit_button('기억 항목 확인하기',type='primary')
    if submit:
        if not memo.strip():
            st.warning('기억나는 내용을 한 가지 이상 적어 주세요.')
        else:
            items=ai_extract(memo.strip())
            if items:
                s.memo=memo.strip();s['items']=items;s.stage=1;st.rerun()
elif s.stage==1:
    if s.verify_summary:
        st.caption('REVIEW COMPLETE')
        st.subheader('기억 조각을 모두 확인했어요.')
        st.write('확인한 기억과 불확실한 부분을 구분해서 다음 회상으로 이어갈게요.')
        summary_metrics(s['items'])
        with st.expander('다음 단계에 사용할 기억',expanded=True):
            for item in s['items']:
                if item['status']!='아님':
                    st.write(f"**{item['kind']}** · {item['content']}")
        st.caption('면접 기본 정보 · 선택 사항')
        with st.form('interview_info'):
            cols=st.columns(2)
            company=cols[0].text_input('회사',value=s.info.get('회사',''),max_chars=100)
            role=cols[1].text_input('직무',value=s.info.get('직무',''),max_chars=100)
            cols=st.columns(2)
            when=cols[0].text_input('면접 일시',value=s.info.get('면접 일시',''),placeholder='예: 2026.11.27 14:00',max_chars=100)
            how=cols[1].selectbox('면접 방식',['기입하지 않음','대면','화상','전화','기타'])
            level=st.selectbox('면접 단계',['기입하지 않음','1차','2차','최종','기타'])
            if st.form_submit_button('AI 복기 계속',type='primary'):
                s.info={'회사':company,'직무':role,'면접 일시':when,'면접 방식':how,'면접 단계':level}
                s.stage=2;next_question();st.rerun()
        if st.button('후보 다시 확인'):
            s.verify_summary=False;st.rerun()
    else:
        st.subheader('이 내용이 내 기억과 맞나요?')
        st.write('원문을 함께 보며 하나씩 확인하세요. 확실하지 않은 기억은 그대로 남겨도 괜찮아요.')
        with st.expander('빠른 메모 원문 보기'):
            st.text(s.memo)
        review_items('verify')
        if st.button('확인 완료 · 복기 시작',type='primary'):
            if any(i['status']=='미확인' or (i['status']!='아님' and not i['content'].strip()) for i in s['items']):
                st.warning('모든 항목을 확인하고, 사용할 항목의 내용을 입력해 주세요.')
            else:
                s.verify_summary=True;st.rerun()
elif s.stage==2:
    q=s.current_question
    phase=0 if q==0 else 1 if q==1 else 3 if q==5 else 2
    phases=['사건 직전 맥락','자유 서술','시간·공간·행동 단서','마지막 순간부터 역순 회상']
    st.caption(f"STEP {phase+1} · 회상 {phase+1} / 4" if q is not None else 'RECALL COMPLETE')
    st.subheader(phases[phase] if q is not None else '지금까지 떠올린 내용을 확인해요.')
    st.caption('불편한 질문은 건너뛰어도 괜찮아요. 기억이 나지 않는 것도 자연스러운 답이에요.')
    if s.info.get('회사') or s.info.get('직무'):
        st.caption(' · '.join(v for v in s.info.values() if v and v!='기입하지 않음'))
    for msg in s.messages:
        with st.chat_message(msg['role']):
            st.write(msg['content'])
    if s.current_question is not None:
        answer=st.chat_input('기억나는 만큼 적어 주세요. 모르겠다면 ‘기억 안 남’이라고 해도 괜찮아요.',max_chars=4000)
        if answer and answer.strip():
            answer=answer.strip()
            s.messages.append({'role':'user','content':answer})
            unknown=answer.replace(' ','').rstrip('.!?') in ['모름','몰라','기억안남','기억안나요','모르겠어요','없어요','넘기기']
            s.misses=s.misses+1 if unknown else 0
            if not unknown:
                s['items'].append(candidate(answer,source='추가 회상 · '+phases[phase]))
            next_question();st.rerun()
    else:
        st.info('충분히 되짚었어요. 지금까지의 내용을 검토해 주세요.')
    c1,c2,c3=st.columns(3)
    if c1.button('이 질문 건너뛰기',disabled=s.current_question is None,use_container_width=True):
        s.misses+=1;next_question();st.rerun()
    if c2.button('현재 단계 완료',disabled=s.current_question is None,use_container_width=True):
        if s.current_question in (2,3,4):
            s.used=list(dict.fromkeys(s.used+[2,3,4]))
        next_question();st.rerun()
    if c3.button('현재 내용으로 최종 검토',type='primary',use_container_width=True):
        s.stage=3;st.rerun()
elif s.stage==3:
    st.subheader('면접의 기억을 마지막으로 확인해요.')
    summary_metrics(s['items'])
    st.caption('추가 회상도 확인이 필요해요. 기억 순서는 직접 지정할 수 있고, 0은 순서 미상으로 남습니다. 순서를 추측해서 맞추지 않아도 괜찮아요.')
    review_items('final')
    with st.form('add_memory'):
        extra=st.text_area('추가하거나 정정할 내용',max_chars=4000)
        if st.form_submit_button('항목 추가') and extra.strip():
            s['items'].append(candidate(extra.strip(),source='최종 검토'));st.rerun()
    if st.button('확인한 내용으로 노트 완성',type='primary'):
        if any(i['status']=='미확인' or (i['status']!='아님' and not i['content'].strip()) for i in s['items']):
            st.warning('모든 항목의 상태와 내용을 확인해 주세요.')
        else:
            s.stage=4;st.rerun()
else:
    st.caption('YOUR MEMORY, YOUR RECORD')
    st.subheader('나의 면접 복기 노트')
    note=render_note(s['items'],s.info,s.memo)
    st.success('직접 확인한 기억을 하나의 기록으로 남겼어요.')
    summary_metrics(s['items'])
    st.info(NOTICE)
    records=[i for i in s['items'] if i['status']!='아님']
    tabs=st.tabs(['요약','기억 순서','평가·불확실','전체 노트'])
    with tabs[0]:
        st.markdown('#### 확인한 기억')
        group=[i for i in records if i['kind']=='기억' and i['status']!='불확실']
        for item in group:
            st.write('• '+item['content'])
        if not group:
            st.caption('확인한 기억이 없어요. 불확실한 내용은 별도 탭에 보존했어요.')
        if s.info:
            st.divider()
            st.caption(' · '.join(v for v in s.info.values() if v and v!='기입하지 않음'))
    with tabs[1]:
        ordered=sorted([i for i in records if i.get('order',0)>0],key=lambda i:i['order'])
        st.caption('사용자가 지정한 순서입니다. 숫자가 없는 내용은 순서 미상으로 남겨요.')
        for item in ordered:
            st.write(f"**{item['order']:02d}** · {item['content']}")
        with st.expander(f"순서 미상 {sum(not i.get('order',0) for i in records)}건",expanded=not ordered):
            for item in records:
                if not item.get('order',0):
                    st.write('• '+item['content'])
    with tabs[2]:
        for item in records:
            if item['kind']!='기억' or item['status']=='불확실':
                st.write(f"**{item['kind']} / {item['status']}** · {item['content']}")
    with tabs[3]:
        st.markdown(note)
    text_note=re.sub(r'(?m)^#{1,2} ', '', note).replace('> '+NOTICE,NOTICE)
    downloads=st.columns(2)
    downloads[0].download_button('텍스트 파일 다운로드 (.txt)',data=text_note.encode('utf-8-sig'),file_name='MEMENTO_면접복기.txt',mime='text/plain',type='primary',use_container_width=True)
    downloads[1].download_button('Markdown 다운로드 (.md)',data=note.encode('utf-8'),file_name='MEMENTO_면접복기.md',mime='text/markdown',use_container_width=True)
    if st.button('다시 검토하기'):
        s.stage=3;st.rerun()
st.divider()
st.caption(NOTICE)
