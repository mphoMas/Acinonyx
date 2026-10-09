import test from 'node:test';
import assert from 'node:assert/strict';
import {createOperationKeys,createContextGuard,validateDates,escapeHTML,properties,roleViews} from '../../public/design-preview/model.mjs';
test('retry reference survives uncertainty and separates properties',()=>{let n=0;const keys=createOperationKeys(()=>String(++n));assert.equal(keys.begin('a','payment'),keys.begin('a','payment'));assert.notEqual(keys.begin('a','payment'),keys.begin('b','payment'));assert.equal(keys.pending('a','payment'),true);keys.acknowledge('a','payment');assert.equal(keys.pending('a','payment'),false);assert.equal(keys.begin('a','payment'),'3');});
test('late responses rejected after switch away and back',()=>{const g=createContextGuard('a'),old=g.snapshot();g.switchTo('b');assert.equal(g.accepts(old),false);g.switchTo('a');assert.equal(g.accepts(old),false);assert.equal(g.accepts(g.snapshot()),true);});
test('dates reject invalid calendar dates and nonpositive stays',()=>{assert.ok(validateDates('2026-02-30','2026-03-02'));assert.ok(validateDates('2026-10-09','2026-10-09'));assert.ok(validateDates('','2026-10-10'));assert.equal(validateDates('2028-02-29','2028-03-01'),'');});
test('untrusted strings are escaped',()=>assert.equal(escapeHTML('<img src="x">&'), '&lt;img src=&quot;x&quot;&gt;&amp;'));
test('launch fixtures and housekeeping visibility reflect scope',()=>{assert.ok(properties.every(p=>p.currency==='MZN'&&p.timezone==='Africa/Maputo'));assert.deepEqual(roleViews.housekeeping,['housekeeping']);});

import {readFileSync} from 'node:fs';
test('text and control boundaries retain minimum contrast',()=>{
 const css=readFileSync(new URL('../../public/design-preview/tokens.css',import.meta.url),'utf8');
 const tokens=Object.fromEntries([...css.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})/g)].map(m=>[m[1],m[2]]));
 const luminance=hex=>{const channels=hex.slice(1).match(/../g).map(h=>parseInt(h,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;};
 const ratio=(a,b)=>{const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
 for(const [fg,bg] of [['ink','surface'],['muted','surface'],['muted','cream'],['success','success-bg'],['warning','warning-bg'],['danger','danger-bg'],['info','info-bg'],['surface','green-dark']])assert.ok(ratio(tokens[fg],tokens[bg])>=4.5,`${fg}/${bg}`);
 assert.ok(ratio(tokens['control-line'],tokens.surface)>=3,'control boundary');
});
