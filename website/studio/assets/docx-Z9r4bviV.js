const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/lib-OyOO8Pzo.js","assets/index-CrhLR2tw.js","assets/index-CHW9QUVU.css","assets/jszip.min-DGyhLLE3.js"])))=>i.map(i=>d[i]);
import{s as e,t}from"./index-CrhLR2tw.js";async function n(n){let r=await t(()=>import(`./lib-OyOO8Pzo.js`).then(t=>e(t.default,1)),__vite__mapDeps([0,1,2,3])),i=globalThis.Buffer,a=i?{buffer:i.from(n)}:{arrayBuffer:n.buffer.slice(n.byteOffset,n.byteOffset+n.byteLength)};return{text:(await r.extractRawText(a)).value.split(`
`).filter(e=>e.trim()!==``).join(`

`).trim(),page_count:null}}export{n as extractTextFromDocx};