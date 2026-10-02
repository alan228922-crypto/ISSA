// Transient coordination only; effects are requests, never Draft mutations.
export function createInteractionController({resolvePointer,inspectEndpoint}) {
  let state={activeTool:'SELECT',phase:'WAITING_FOR_START',pendingMemberStart:null,basisDraft:null,snapResolution:null,dynamicInput:null,preview:null,gesture:null,temporaryOrtho:false};
  const clear=()=>{state={...state,phase:'WAITING_FOR_START',pendingMemberStart:null,basisDraft:null,preview:null,dynamicInput:null,snapResolution:null,temporaryOrtho:false};};
  return Object.freeze({getState:()=>state,dispatch(event,context){
    const effects=[];
    if(event.type==='SELECT_TOOL'){clear();state={...state,activeTool:event.tool};}
    if(event.type==='CANCEL'){clear();state={...state,activeTool:'SELECT'};}
    if(event.type==='DRAFT_CHANGED' && state.basisDraft && state.basisDraft!==context.draft)clear();
    if(event.type==='POINTER_RESOLVE')state={...state,snapResolution:resolvePointer({...event,origin:state.pendingMemberStart?.worldPoint || event.origin,ortho:context.settings?.ortho,gridEnabled:context.settings?.gridSnap})};
    if(event.type==='CONFIRM_POINT'||event.type==='PRECISE_POINT'){
      const resolution=event.type==='PRECISE_POINT'?{kind:'PRECISE',worldPoint:event.worldPoint,axis:null}:event.resolution;
      if(!context.readOnly&&resolution&&state.activeTool==='MEMBER'){
        const endpoint=resolution.kind==='NODE'?{kind:'EXISTING_NODE',nodeClientKey:resolution.nodeClientKey,worldPoint:{...resolution.worldPoint}}:{kind:'PROVISIONAL_POINT',worldPoint:{...resolution.worldPoint}};
        const inspected=inspectEndpoint(context.draft,endpoint);
        const error=endpoint.kind==='PROVISIONAL_POINT'&&context.draft.schema_version==='physical-draft-v2'?(inspected.collocatedNodeClientKeys.length?'EDITOR_EXPLICIT_NODE_REQUIRED':inspected.passingMemberClientKeys.length>=2?'EDITOR_UNJOINED_CROSSING_ENDPOINT':null):null;
        if(error)effects.push({type:'ERROR',code:error,message:error==='EDITOR_UNJOINED_CROSSING_ENDPOINT'?'此处是尚未连接的构件交点；请先用「节点」工具建立连接':'此处已有节点，请通过节点捕捉明确选择节点。'});
        else if(!state.pendingMemberStart)state={...state,pendingMemberStart:endpoint,basisDraft:context.draft,phase:'WAITING_FOR_END'};
        else effects.push({type:'REQUEST_MEMBER_COMMIT',start:state.pendingMemberStart,end:endpoint});
      }
      if(!context.readOnly&&resolution&&state.activeTool==='NODE')effects.push({type:'REQUEST_NODE_CONFIRM',resolution});
    }
    if(event.type==='PAN_START')state={...state,gesture:'MIDDLE_PAN'};
    if(event.type==='PAN_END')state={...state,gesture:null};
    if(event.type==='EDITOR_RESULT'&&event.ok)clear();
    return {state,consumed:state.activeTool!=='SELECT',effects};
  }});
}
