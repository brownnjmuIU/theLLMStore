const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/jszip.min-DGyhLLE3.js","assets/index-CrhLR2tw.js","assets/index-CHW9QUVU.css"])))=>i.map(i=>d[i]);
import{s as e,t}from"./index-CrhLR2tw.js";function n(e){let t=/slide(\d+)\.xml$/.exec(e);return t?.[1]?Number(t[1]):2**53-1}function r(e){return e.replace(/&lt;/g,`<`).replace(/&gt;/g,`>`).replace(/&quot;/g,`"`).replace(/&apos;/g,`'`).replace(/&#(\d+);/g,(e,t)=>String.fromCodePoint(Number(t))).replace(/&amp;/g,`&`)}function i(e){let t=[];for(let n of e.matchAll(/<a:p\b[^>]*>([\s\S]*?)<\/a:p>/g)){let e=n[1]??``,i=``;for(let t of e.matchAll(/<a:t\b[^>]*>([\s\S]*?)<\/a:t>/g))i+=r(t[1]??``);let a=i.trim();a&&t.push(a)}return t}async function a(r){let{default:a}=await t(async()=>{let{default:t}=await import(`./jszip.min-DGyhLLE3.js`).then(t=>e(t.t(),1));return{default:t}},__vite__mapDeps([0,1,2])),o=await a.loadAsync(r),s=Object.keys(o.files).filter(e=>/^ppt\/slides\/slide\d+\.xml$/.test(e)).sort((e,t)=>n(e)-n(t)),c=[];for(let e of s){let t=o.file(e);if(!t)continue;let n=i(await t.async(`string`));n.length>0&&c.push(n.join(`
`))}return{text:c.join(`

---

`).trim(),page_count:s.length}}export{a as extractTextFromPptx};