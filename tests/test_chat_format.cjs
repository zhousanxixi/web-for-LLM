// Requires jsdom: npm install --no-save --package-lock=false jsdom
// Run: node tests/test_chat_format.cjs
const {JSDOM}=require('jsdom');const fs=require('fs'),assert=require('node:assert/strict');
const root=require('node:path').resolve(__dirname,'../web');
const w=new JSDOM('<p id="answer"></p>',{runScripts:'outside-only',url:'http://localhost'}).window;
w.eval(fs.readFileSync(root+'/chat-format.js','utf8'));const a=w.document.querySelector('p');
const render=t=>w.chatFormat.render(a,t);let n=0;
function check(fn){fn();n++}
render('**香港科学馆（Museum） **，推荐参观。');check(()=>assert.equal(a.querySelector('strong').textContent,'香港科学馆（Museum）'));check(()=>assert(!a.textContent.includes('**')));
render('[place-70:0](https://example.org/a) | [guide-science:0]\n(https://example.org/b)');check(()=>assert.equal(a.querySelectorAll('a').length,2));check(()=>assert(!/place-|guide-/.test(a.textContent)));check(()=>assert.equal(a.querySelector('a').rel,'noopener noreferrer'));
render('参观 [guide-science:0]。');check(()=>assert.equal(a.textContent,'参观 。'));
render('<img src=x onerror=alert(1)> **safe** [x](javascript:alert)');check(()=>assert(!a.querySelector('img')));check(()=>assert(!a.querySelector('a')));check(()=>assert(a.textContent.includes('<img')));
render('天气 **良好');render('天气 **良好** [place-70:0]');check(()=>assert.equal(a.querySelector('strong').textContent,'良好'));check(()=>assert(!a.textContent.includes('place-')));
render('[官方网站](https://example.org)');check(()=>assert.equal(a.querySelector('a').textContent,'官方网站'));
console.log(n+' answer-format checks passed');w.close();
