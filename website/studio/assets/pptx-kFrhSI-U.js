const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/jszip.min-Dn3Qqvqr.js","assets/_commonjs-dynamic-modules-Dt2RjKzG.js","assets/jszip.min-BD58qjAi.js"])))=>i.map(i=>d[i]);
import{_ as l}from"./index-rtwQmVdK.js";function c(a){const e=/slide(\d+)\.xml$/.exec(a);return e?.[1]?Number(e[1]):Number.MAX_SAFE_INTEGER}function p(a){return a.replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&apos;/g,"'").replace(/&#(\d+);/g,(e,r)=>String.fromCodePoint(Number(r))).replace(/&amp;/g,"&")}function u(a){const e=[];for(const r of a.matchAll(/<a:p\b[^>]*>([\s\S]*?)<\/a:p>/g)){const s=r[1]??"";let o="";for(const n of s.matchAll(/<a:t\b[^>]*>([\s\S]*?)<\/a:t>/g))o+=p(n[1]??"");const t=o.trim();t&&e.push(t)}return e}async function m(a){const{default:e}=await l(async()=>{const{default:t}=await import("./jszip.min-Dn3Qqvqr.js").then(n=>n.j);return{default:t}},__vite__mapDeps([0,1,2])),r=await e.loadAsync(a),s=Object.keys(r.files).filter(t=>/^ppt\/slides\/slide\d+\.xml$/.test(t)).sort((t,n)=>c(t)-c(n)),o=[];for(const t of s){const n=r.file(t);if(!n)continue;const i=u(await n.async("string"));i.length>0&&o.push(i.join(`
`))}return{text:o.join(`

---

`).trim(),page_count:s.length}}export{m as extractTextFromPptx};
