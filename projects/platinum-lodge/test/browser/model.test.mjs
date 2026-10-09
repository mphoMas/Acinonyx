import test from 'node:test';
import assert from 'node:assert/strict';
import {createOperationKeys,createContextGuard,validateDates,escapeHTML,properties,roleViews} from '../../public/design-preview/model.mjs';
test('retry reference survives uncertainty and separates properties',()=>{let n=0;const keys=createOperationKeys(()=>String(++n));assert.equal(keys.begin('a','payment'),keys.begin('a','payment'));assert.notEqual(keys.begin('a','payment'),keys.begin('b','payment'));assert.equal(keys.pending('a','payment'),true);keys.acknowledge('a','payment');assert.equal(keys.pending('a','payment'),false);assert.equal(keys.begin('a','payment'),'3');});
test('late responses rejected after switch away and back',()=>{const g=createContextGuard('a'),old=g.snapshot();g.switchTo('b');assert.equal(g.accepts(old),false);g.switchTo('a');assert.equal(g.accepts(old),false);assert.equal(g.accepts(g.snapshot()),true);});
test('dates reject invalid calendar dates and nonpositive stays',()=>{assert.ok(validateDates('2026-02-30','2026-03-02'));assert.ok(validateDates('2026-10-09','2026-10-09'));assert.ok(validateDates('','2026-10-10'));assert.equal(validateDates('2028-02-29','2028-03-01'),'');});
test('untrusted strings are escaped',()=>assert.equal(escapeHTML('<img src="x">&'), '&lt;img src=&quot;x&quot;&gt;&amp;'));
test('launch fixtures and housekeeping visibility reflect scope',()=>{assert.ok(properties.every(p=>p.currency==='MZN'&&p.timezone==='Africa/Maputo'));assert.deepEqual(roleViews.housekeeping,['housekeeping']);});
