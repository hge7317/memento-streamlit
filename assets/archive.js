export default function({parentElement,data}) {
  const KEY='memento.completedNotes.v1';
  const status=parentElement.querySelector('.storage-status');
  const section=parentElement.querySelector('.archive');
  const search=parentElement.querySelector('.search');
  const list=parentElement.querySelector('.list');
  const detail=parentElement.querySelector('.detail');
  const count=parentElement.querySelector('.count');
  let records=[],deleted=[],healthy=true;
  const clean=r=>r&&typeof r==='object'&&['id','title','createdAt','updatedAt','note'].every(k=>typeof r[k]==='string')?Object.fromEntries(['id','title','createdAt','updatedAt','note'].map(k=>[k,r[k]])):null;
  function message(text,error=false){status.textContent=text;status.classList.toggle('error',error)}
  function read(){
    try{
      const raw=localStorage.getItem(KEY);
      const value=raw===null?{notes:[],deleted:[]}:JSON.parse(raw);
      const notes=Array.isArray(value)?value:value.notes;
      const removed=Array.isArray(value)?[]:value.deleted;
      if(!Array.isArray(notes)||notes.some(r=>!clean(r))||!Array.isArray(removed)||removed.some(id=>typeof id!=='string'))throw new Error('invalid');
      records=notes.map(clean);deleted=removed;healthy=true;return true;
    }catch(e){healthy=false;message('브라우저 보관함을 읽을 수 없어요. 브라우저 저장 설정을 확인해 주세요. 기존 데이터는 덮어쓰지 않았어요.',true);return false}
  }
  function persist(next){
    if(!healthy)return false;
    try{localStorage.setItem(KEY,JSON.stringify({notes:next,deleted}));records=next;return true}
    catch(e){message('자동 보관에 실패했어요. 저장 공간이 부족하거나 브라우저가 저장을 막고 있어요. 노트를 파일로 내려받아 주세요.',true);return false}
  }
  function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
  function button(text,action,cls){const b=node('button',text,cls);b.type='button';b.onclick=action;return b}
  function date(s){const d=new Date(s);return Number.isNaN(d.getTime())?s:d.toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})}
  function download(r){const text=r.note.replace(/^#{1,2} /gm,'').replace(/^> /gm,'');const url=URL.createObjectURL(new Blob(['\uFEFF',text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='MEMENTO_'+r.title.replace(/[\\/:*?"<>|]/g,'_').slice(0,60)+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
  function open(r){
    parentElement.querySelector('.archive').dataset.openId=r.id;
    detail.replaceChildren(node('h3',r.title),node('p','작성 '+date(r.createdAt),'meta'),button('텍스트 다운로드',()=>download(r),'primary'),button('닫기',()=>{delete section.dataset.openId;detail.replaceChildren()}),node('div',r.note.replace(/^#{1,2} /gm,'').replace(/^> /gm,''),'preview'));
  }
  function render(){
    list.replaceChildren();count.textContent='이 브라우저에 보관한 복기 '+records.length+'개';
    const query=search.value.trim().toLowerCase();
    const matches=records.filter(r=>(r.title+' '+r.note).toLowerCase().includes(query)).sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt));
    if(!matches.length)list.append(node('p',records.length?'검색 결과가 없어요.':'아직 보관한 기록이 없어요. 복기 노트를 완성하면 여기에 자동으로 쌓여요.','empty'));
    matches.forEach(r=>{
      const card=node('article',undefined,'card');card.append(node('h3',r.title),node('p','작성 '+date(r.createdAt),'meta'),button('기록 열기',()=>open(r),'primary'),button('텍스트 다운로드',()=>download(r)));
      const remove=button('삭제',()=>{
        const confirm=node('div');confirm.append(node('p','이 기록을 이 브라우저에서 삭제할까요? 파일로 내려받은 사본은 유지돼요.','meta'),button('삭제 확인',()=>{
          if(!read())return;deleted=[...new Set([...deleted,r.id])];
          if(persist(records.filter(x=>x.id!==r.id))){if(section.dataset.openId===r.id){delete section.dataset.openId;detail.replaceChildren()}message('보관함에서 기록을 삭제했어요.');render()}
        },'danger'),button('취소',()=>confirm.remove()));card.append(confirm);remove.disabled=true;
      },'danger');card.append(remove);list.append(card)
    });
    const opened=records.find(r=>r.id===section.dataset.openId);if(opened)open(opened);
  }
  read();
  const incoming=clean(data.record);
  if(incoming&&healthy&&!deleted.includes(incoming.id)){
    const old=records.find(r=>r.id===incoming.id);
    // Upsert the same note rather than duplicating it on each app rerun.
    // A deliberately deleted note is not silently recreated by opening the archive.
    if(!data.show&&(!old||old.note!==incoming.note||old.updatedAt!==incoming.updatedAt)){
      if(persist([...records.filter(r=>r.id!==incoming.id),incoming]))message('이 복기 노트를 이 브라우저에 자동 보관했어요.');
    }else message(data.show?'같은 브라우저에서 다시 접속하면 기록을 볼 수 있어요.':'이 복기 노트는 이 브라우저에 보관되어 있어요.');
  }else if(healthy&&incoming&&deleted.includes(incoming.id)){message('이 노트는 보관함에서 삭제한 기록이에요. 현재 화면에서 파일 다운로드는 가능해요.')}else if(healthy){message('완성한 노트는 이 브라우저에 자동 보관돼요. 브라우저 데이터 삭제 시 기록도 사라집니다.')}
  section.hidden=!data.show;
  if(data.show)render();
  search.oninput=render;
  function onStorage(e){if(e.key===KEY&&read()){render();message('보관함을 새로 불러왔어요.')}}
  window.addEventListener('storage',onStorage);
  return ()=>window.removeEventListener('storage',onStorage);
}
