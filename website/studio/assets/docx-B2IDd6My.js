const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/index-9Ub_VBTT.js","assets/_commonjs-dynamic-modules-Dt2RjKzG.js","assets/jszip.min-BD58qjAi.js"])))=>i.map(i=>d[i]);
import{_ as n}from"./index-rtwQmVdK.js";async function i(t){const e=await n(()=>import("./index-9Ub_VBTT.js").then(r=>r.i),__vite__mapDeps([0,1,2])),a=globalThis.Buffer,o=a?{buffer:a.from(t)}:{arrayBuffer:t.buffer.slice(t.byteOffset,t.byteOffset+t.byteLength)};return{text:(await e.extractRawText(o)).value.split(`
`).filter(r=>r.trim()!=="").join(`

`).trim(),page_count:null}}export{i as extractTextFromDocx};
