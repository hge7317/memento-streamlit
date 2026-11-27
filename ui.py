"""Presentation and source-first review controls."""
import base64
from pathlib import Path
import html
import streamlit as st
from engine import KINDS

@st.cache_data
def style():
    fonts=''
    for family,name,fmt in [('Pretendard','PretendardVariable.woff2','woff2'),('NanumSquareNeo','NanumSquareNeo-Variable.woff2','woff2')]:
        p=Path(__file__).parent/'assets'/name
        if p.exists():
            data=base64.b64encode(p.read_bytes()).decode()
            fonts+=f"@font-face{{font-family:'{family}';src:url(data:font/{fmt};base64,{data}) format('{fmt}');font-weight:100 900;font-display:swap;}}"
    return '<style>'+fonts+'''
    html,body,[data-testid="stApp"],input,textarea,button,[data-testid="stMarkdownContainer"],label {
        font-family:'Pretendard',-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo',sans-serif;
    }
    .block-container {max-width:1050px;padding:2rem 2.5rem 4rem}
    h1,h2 {font-family:'NanumSquareNeo','Pretendard',sans-serif!important;font-weight:450!important;letter-spacing:-.035em;line-height:1.4!important;word-break:keep-all}
    h1 {font-size:clamp(2rem,4vw,3.3rem)!important;padding:1rem 0!important}
    h3 {font-family:'Pretendard',sans-serif!important;font-weight:650!important;letter-spacing:-.035em;font-size:1.65rem!important}
    p {line-height:1.8;font-size:1rem}
    .brand {font-size:1.9rem;font-weight:850;letter-spacing:-.07em;padding:.3rem 0 1.5rem;border-bottom:1px solid #b8cdde;margin-bottom:1.4rem}
    .brand span {font-size:.75rem;letter-spacing:.14em;font-weight:550;color:#536d84;margin-left:1.1rem}
    [data-testid="stCaptionContainer"] p {color:#4c657b;font-size:.9rem;line-height:1.7}
    div[data-testid="stForm"] {border:none!important;box-shadow:none!important;padding:0!important}
    div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:18px}
    button[kind="primary"],button[kind="primaryFormSubmit"] {background:#90A3B4!important;color:#22374B!important;border:none!important}
    .stButton>button,.stDownloadButton>button,.stFormSubmitButton>button {border-radius:999px;min-height:2.8rem;font-weight:650;padding:.55rem 1.15rem;box-shadow:none}
    [data-testid="stChatMessage"] {background:#c8dced;border-radius:20px;padding:1.2rem}
    [data-testid="stChatMessage"] p {font-size:1.05rem}
    [data-testid="stMetricValue"] {font-size:1.8rem;font-weight:550}
    .memory-tag {display:inline-block;font-size:.78rem;font-weight:650;letter-spacing:.04em;color:#36536e;background:#c8dced;border-radius:999px;padding:.2rem .7rem;margin-bottom:.7rem}
    .memory-tag.uncertain {color:#805c20;background:#fbf1d9}
    .memory-tag.evaluation {color:#655377;background:#f1ecf6}
    .memory-text {font-size:1.15rem;line-height:1.8;word-break:keep-all;white-space:pre-wrap;color:#22374b;padding:.4rem 0 .7rem}
    .memory-status {color:#4c657b;font-size:.85rem;margin-bottom:.7rem}
    @media(max-width:700px){.block-container{padding:1.4rem 1rem 3rem}.brand span{display:block;margin:.4rem 0 0}.stButton>button{padding:.5rem .7rem}}
    </style>'''


def apply_style():
    st.markdown(style(),unsafe_allow_html=True)


def summary_metrics(items):
    counts=[sum(i['status']==v for i in items) for v in ['맞음','수정','불확실','아님']]
    for col,title,count in zip(st.columns(4),['확인','수정','불확실','제외'],counts):
        col.metric(title,f'{count}건')


def memory_card(item,idx,prefix,allow_order=False):
    key=f'{prefix}_{idx}'
    def set_status(value):
        item['status']=value
    with st.container(border=True):
        tag={'기억':('FACT · 사실 후보',''),'불확실':('UNCERTAIN · 불확실','uncertain'),'평가·감정':('EVALUATION · 평가·감정','evaluation')}[item['kind']]
        st.markdown(f'<span class="memory-tag {tag[1]}">{tag[0]}</span>',unsafe_allow_html=True)
        st.caption(f"{idx+1:02d} · {item['source']} · {item['status']}")
        st.markdown('<div class="memory-text">'+html.escape(item['content'])+'</div>',unsafe_allow_html=True)
        with st.expander('원문 확인'):
            st.text(item['original'])
        if item['status']=='아님':
            st.caption('제외했어요. 이후 회상과 복기 노트에 사용하지 않습니다.')
            if st.button('이 항목 다시 수정',key=key+'_restore'):
                item['status']='미확인';st.session_state[key+'_editing']=True;st.rerun()
        else:
            cols=st.columns([1,1.4,1,1])
            cols[0].button('맞아요',type='primary' if item['status']=='맞음' else 'secondary',key=key+'_yes',on_click=set_status,args=('맞음',),use_container_width=True)
            cols[1].button('확실하지 않아요',type='primary' if item['status']=='불확실' else 'secondary',key=key+'_unknown',on_click=set_status,args=('불확실',),use_container_width=True)
            if cols[2].button('수정',type='primary' if item['status']=='수정' else 'secondary',key=key+'_edit',use_container_width=True):
                st.session_state[key+'_editing']=True
            cols[3].button('내용 없음',key=key+'_no',on_click=set_status,args=('아님',),use_container_width=True)
        if st.session_state.get(key+'_editing'):
            with st.form(key+'_edit_form'):
                content=st.text_area('기억 내용 수정',value=item['content'],max_chars=4000)
                kind=st.selectbox('내용 구분',KINDS,index=KINDS.index(item['kind']))
                if st.form_submit_button('수정 내용 확인'):
                    if content.strip():
                        item.update(content=content.strip(),kind=kind,status='수정')
                        st.session_state[key+'_editing']=False;st.rerun()
                    else:
                        st.warning('내용을 입력하거나 이 항목을 제외해 주세요.')
        if allow_order and item['status']!='아님':
            item['order']=st.number_input('기억 순서 · 0은 순서 미상',min_value=0,max_value=999,value=item.get('order',0),step=1,key=key+'_order')
