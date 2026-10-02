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
    if(event.type==='PAN_START')state={...state,gesture:'MIDDLE_PAN'};
    if(event.type==='PAN_END')state={...state,gesture:null};
    if(event.type==='EDITOR_RESULT'&&event.ok)clear();
    return {state,consumed:state.activeTool!=='SELECT',effects};
  }});
}
