import {createUiIcon} from '../../ui/icons.js';

// 只投影已有Run元资料；唯一选择权威仍是原native select与run-context。
export function bindLearningPresentation({root,select}) {
  const context=root.querySelector('[data-learning-run-context]');
  const history=root.querySelector('#workspace-history');
  const title=document.createElement('h2');title.textContent='历史分析记录';title.prepend(createUiIcon('history'));
  const note=document.createElement('p');note.textContent='选择一份已保存分析；计算依据、设计说明、证据与反思将使用同一次分析。';
  const list=document.createElement('div');list.className='learning-history-list';
  const empty=document.createElement('p');empty.className='learning-notice';empty.textContent='还没有分析记录。请回到建模，保存并完成分析。';history.replaceChildren(title,note,list,empty);
  const buttons=new Map();let rows=[];
  const number=id=>[...rows].sort((a,b)=>a.analysis_run_id-b.analysis_run_id).findIndex(r=>r.analysis_run_id===id)+1;
  const sync=()=>{for(const [id,button] of buttons)button.setAttribute('aria-pressed',String(String(id)===select.value));};
  return Object.freeze({
    renderHistory(runs) {
      rows=[...runs];empty.hidden=rows.length>0;
      const ids=new Set(rows.map(r=>r.analysis_run_id));
      for(const [id,button] of buttons)if(!ids.has(id)){button.remove();buttons.delete(id);}
      rows.forEach((row,index)=>{
        let button=buttons.get(row.analysis_run_id);
        if(!button){button=document.createElement('button');button.type='button';button.dataset.historyRun=String(row.analysis_run_id);button.addEventListener('click',()=>{select.value=String(row.analysis_run_id);select.dispatchEvent(new Event('change',{bubbles:true}));});buttons.set(row.analysis_run_id,button);}
        button.dataset.runStatus=row.status;button.dataset.stale=String(Boolean(row.is_stale));
        const name=document.createElement('strong');name.textContent=`第 ${number(row.analysis_run_id)} 次分析`;
        const state=document.createElement('span');state.className='learning-badge';state.textContent=row.status==='SUCCESS'?'已完成':'未完成';
        const source=document.createElement('span');source.textContent=`已保存草稿 v${row.source_draft_version} · ${row.is_stale?'历史版本，不代表当前草稿':'与当前已保存草稿一致' }`;
        const date=document.createElement('time');date.dateTime=row.created_at;date.textContent=new Date(row.created_at).toLocaleString('zh-CN',{hour12:false});
        button.replaceChildren(name,state,source,date);if(list.children[index]!==button)list.insertBefore(button,list.children[index]||null);
      });sync();
    },
    setSelection(metadata,{loading=false}={}) {
      sync();root.dataset.learningSelection=metadata?(loading?'loading':metadata.status==='SUCCESS'?'ready':'failed'):'empty';
      const emptyNote=root.querySelector('[data-ux-summary-empty]');
      if(emptyNote)emptyNote.textContent=metadata?(loading?'正在载入所选分析，请稍候…':metadata.status!=='SUCCESS'?'这次分析未完成，没有可查看的学习资料。请选择其他分析记录。':'请先选择一次分析。'):'请先选择一次分析。';
      context.dataset.stale=String(Boolean(metadata?.is_stale));
      context.textContent=metadata?`第 ${number(metadata.analysis_run_id)} 次分析 · 已保存草稿 v${metadata.source_draft_version} · ${loading?'正在载入…':metadata.status!=='SUCCESS'?'分析未完成，无可用结果':metadata.is_stale?'历史证据，不代表当前草稿':'所选分析的数值与来源'}`:'尚未选定分析记录。';
    },
    showRequestError(){if(root.dataset.learningSelection==='loading'){root.dataset.learningSelection='error';const emptyNote=root.querySelector('[data-ux-summary-empty]');if(emptyNote)emptyNote.textContent='所选分析载入失败，请重新选择后重试。';context.textContent='所选分析暂时无法载入，请重新选择分析记录后重试。';}}
  });
}
