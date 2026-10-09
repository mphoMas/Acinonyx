import {properties,roleViews,fixtures,escapeHTML as e,validateDates,createContextGuard,createOperationKeys} from './model.mjs';
const $=id=>document.getElementById(id),guard=createContextGuard(properties[0].id),keys=createOperationKeys();
let view='today',dirty=false,pendingProperty=null;
const labels={today:'Today',reservations:'Reservations',billing:'Billing',housekeeping:'Housekeeping',portfolio:'Portfolio'};
$('property').innerHTML=properties.map(p=>`<option value="${p.id}">${e(p.name)}</option>`).join('');
const announce=s=>$('announcement').textContent=s;
function go(next){view=next;render();$('workspace').focus();}
function render(){
 const p=properties.find(p=>p.id===guard.current),f=fixtures[p.id],allowed=roleViews[$('role').value],state=$('scenario').value;
 if(!allowed.includes(view))view=allowed[0];
 $('navigation').innerHTML=allowed.map(v=>`<button data-view="${v}" aria-current="${v===view?'page':'false'}">${labels[v]}</button>`).join('');
 document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>go(b.dataset.view));
 const heading=`<div class="heading"><div><p class="eyebrow">${e(p.name)} · ${p.currency} · ${p.timezone}</p><h1>${labels[view]}</h1><p class="muted">Fictional operational workspace · Sample data has no live freshness guarantee</p></div></div>`;
 const messages={loading:'Loading preview. No previous-property records are shown.',empty:'No sample records in this state. Choose Normal to return.',error:'Unable to load. Existing drafts are retained; no mutation is retried.',denied:'Access unavailable. Production permissions require server enforcement.',stale:'Read-only: data freshness is unverified. Reconnect and refresh before making changes.',conflict:'Version conflict: preserve the draft and review the latest record before resubmitting.',pending:'Payment pending: wait for authoritative provider status. Do not submit another payment.',unknown:'Payment outcome unknown: reconcile using the original operation reference before retrying.'};
 $('workspace').setAttribute('aria-busy',String(state==='loading'));
 if(['loading','empty','error','denied'].includes(state)){ $('workspace').innerHTML=heading+`<section class="panel state-message" role="status"><h2>${state==='denied'?'Permission required':labels[view]}</h2><p>${messages[state]}</p>${state==='error'?'<button id="retry">Retry preview loading</button>':''}</section>`;if($('retry'))$('retry').onclick=()=>{$('scenario').value='ready';render();};return;}
 const banner=state==='ready'?'':`<div class="state-message warning" role="status">${messages[state]}</div>`;
 const money=n=>new Intl.NumberFormat('en-MZ',{style:'currency',currency:p.currency}).format(n/100);
 let body='';
 if(view==='today')body=`<div class="metrics"><section class="panel metric"><h2>Arrivals</h2><strong>${f.arrivals}</strong></section><section class="panel metric"><h2>Departures</h2><strong>${f.departures}</strong></section><section class="panel metric"><h2>Ready rooms</h2><strong>${f.ready}</strong></section></div><section class="panel"><h2>Needs attention</h2><div class="task"><div><h3>Inspect arrival room ${e(f.rooms[0].number)}</h3><p>Owner: supervisor · Due before guest arrival · Sample age: 10 minutes</p></div><button data-next="housekeeping">Review room</button></div><div class="task"><div><h3>Review arrival exceptions</h3><p>Owner: reception · Verify dates, room readiness and payment status separately</p></div><button data-next="reservations">Open arrivals</button></div></section>`;
 if(view==='reservations')body=`<section class="panel"><div class="actions"><h2>Front desk queue</h2><button id="new-reservation" class="primary" ${state!=='ready'?'disabled':''}>New preview draft</button></div><div class="table-wrap" role="region" aria-label="Sample reservations" tabindex="0"><table><thead><tr><th>Guest</th><th>Room</th><th>Stay status</th><th>Action</th></tr></thead><tbody>${f.stays.map(s=>`<tr><td>${e(s.guest)}</td><td>${e(s.room)}</td><td>${e(s.status)}</td><td>Review readiness before check-in</td></tr>`).join('')}</tbody></table></div><p>Room, occupancy, housekeeping and payment states remain separate. Calendar inventory and check-in require the agreed backend contract.</p></section>`;
 if(view==='billing')body=`<section class="panel"><h2>Sample folio review</h2><div class="table-wrap" role="region" aria-label="Sample folios" tabindex="0"><table><thead><tr><th>Room</th><th>Fixture balance</th><th>Payment status</th><th>Reconciliation</th></tr></thead><tbody>${f.stays.map(s=>`<tr><td>${e(s.room)}</td><td>${money(s.balance)}</td><td>${state==='pending'?'Pending':state==='unknown'?'Unknown':'Not connected'}</td><td>Unverified</td></tr>`).join('')}</tbody></table></div><p>Charging, refunds, tax invoices and checkout are unavailable until authoritative ledger and payment services are integrated. Never infer payment success from a browser timeout.</p></section>`;
 if(view==='housekeeping')body=`<div class="room-grid">${f.rooms.map(r=>`<section class="panel room"><h2>Room ${e(r.number)}</h2><p><span class="status ${r.cleaning==='Clean'?'':'warning'}">${e(r.cleaning)}</span> · ${e(r.occupancy)}</p><p>Priority: ${e(r.priority)}</p><p>Assigned: ${e(r.assigned)}</p><button class="room-action" ${state!=='ready'?'disabled':''}>Preview inspection request</button></section>`).join('')}</div><p>Guest identities and financial details are omitted from the housekeeping workspace. Backend task ownership, inspection authority and audit persistence remain required.</p>`;
 if(view==='portfolio')body=`<section class="panel"><h2>Mozambique property overview</h2><p>Both properties are fictional; the initial live pilot is Platinum Hotel only. Compare operating counts, with explicit property context.</p><div class="room-grid">${properties.map(q=>`<section class="panel"><h3>${e(q.name)}</h3><p>${q.currency} · ${q.timezone}</p><p>${fixtures[q.id].arrivals} sample arrivals · ${fixtures[q.id].ready} sample ready rooms</p><p>Ledger totals and KPI definitions: awaiting backend contract</p></section>`).join('')}</div></section>`;
 $('workspace').innerHTML=heading+banner+body;
 document.querySelectorAll('[data-next]').forEach(b=>{b.disabled=!allowed.includes(b.dataset.next);b.onclick=()=>go(b.dataset.next);});
 if($('new-reservation'))$('new-reservation').onclick=()=>{$('reservation-dialog').showModal();};
 document.querySelectorAll('.room-action').forEach(b=>b.onclick=()=>announce('Inspection request preview only. No task was submitted.'));
}
function switchProperty(){guard.switchTo(pendingProperty);$('reservation-form').reset();$('form-feedback').textContent='';dirty=false;pendingProperty=null;render();announce('Property changed. Previous property records and draft cleared.');}
$('property').onchange=()=>{pendingProperty=$('property').value;if(dirty){$('switch-dialog').showModal();}else switchProperty();};
function keep(){pendingProperty=null;$('property').value=guard.current;$('switch-dialog').close();}
$('keep-draft').onclick=keep;$('switch-dialog').oncancel=keep;
$('discard-draft').onclick=()=>{$('switch-dialog').close();switchProperty();};
$('role').onchange=()=>{dirty=false;$('reservation-form').reset();$('form-feedback').textContent='';render();};
$('scenario').onchange=render;
$('reservation-form').oninput=()=>dirty=true;
$('close-reservation').onclick=()=>$('reservation-dialog').close();
$('reservation-form').onsubmit=event=>{event.preventDefault();const error=validateDates($('arrival').value,$('departure').value);if(error){$('form-feedback').textContent=error;return;}const key=keys.begin(guard.current,'reservation-draft');$('form-feedback').textContent=`Preview draft validated. Stable local operation reference: ${key}. Nothing sent or saved.`;dirty=true;};
render();
