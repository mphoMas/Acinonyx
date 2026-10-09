export const properties = Object.freeze([
  {id:'sample-a',name:'Sample Lodge A',currency:'MZN',timezone:'Africa/Maputo'},
  {id:'sample-b',name:'Sample Lodge B',currency:'MZN',timezone:'Africa/Maputo'},
]);
export const roleViews = Object.freeze({manager:['today','reservations','billing','housekeeping','portfolio'],reception:['today','reservations','billing'],finance:['billing','portfolio'],housekeeping:['housekeeping']});
export const fixtures = Object.freeze({
  'sample-a': {arrivals:6,departures:4,ready:18,rooms:[{number:'A101',cleaning:'Dirty',occupancy:'Vacant',priority:'Arrival due',assigned:'Sample staff A'},{number:'A102',cleaning:'Inspection',occupancy:'Vacant',priority:'Arrival due',assigned:'Sample staff B'},{number:'A103',cleaning:'Clean',occupancy:'Occupied',priority:'Routine',assigned:'Sample staff A'}],stays:[{guest:'Sample Guest 01',room:'A101',status:'Room not ready',balance:640000},{guest:'Sample Guest 02',room:'A103',status:'In-house',balance:0}]},
  'sample-b': {arrivals:3,departures:2,ready:11,rooms:[{number:'B201',cleaning:'Cleaning',occupancy:'Vacant',priority:'Arrival due',assigned:'Sample staff C'},{number:'B202',cleaning:'Clean',occupancy:'Vacant',priority:'Routine',assigned:'Sample staff D'}],stays:[{guest:'Sample Guest 11',room:'B201',status:'Room not ready',balance:18000},{guest:'Sample Guest 12',room:'B202',status:'Confirmed',balance:9000}]},
});
export function escapeHTML(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
export function validateDates(arrival,departure){if(!/^\d{4}-\d{2}-\d{2}$/.test(arrival)||!/^\d{4}-\d{2}-\d{2}$/.test(departure))return 'Enter both dates.';if([arrival,departure].some(d=>{const date=new Date(d+'T00:00:00Z');return Number.isNaN(date.valueOf())||date.toISOString().slice(0,10)!==d;}))return 'Enter valid calendar dates.';if(departure<=arrival)return 'Departure must follow arrival.';return '';}
// Frontend primitive only. It does not implement server idempotency or authorization.
export function createOperationKeys(uuid=()=>crypto.randomUUID()){
  const keys=new Map();
  return {
    begin(context,operation){const scope=JSON.stringify([context,operation]);if(!keys.has(scope))keys.set(scope,uuid());return keys.get(scope);},
    acknowledge(context,operation){keys.delete(JSON.stringify([context,operation]));},
    pending(context,operation){return keys.has(JSON.stringify([context,operation]));},
  };
}
// Responses carrying an earlier context/version must not update a new workspace.
export function createContextGuard(initial){let context=initial,version=0;return {
  get current(){return context;},
  snapshot(){return {context,version};},
  switchTo(next){context=next;version++;},
  accepts(snapshot){return snapshot.context===context&&snapshot.version===version;},
};}
