import{_ as g}from"./ppllm-app.js";const P=.1,T=.5;let w=!1;async function h(){const o=await g(()=>import("./pdf-DMRcuM1e.js"),[]);if(!w){const r=o.GlobalWorkerOptions;if(!r.workerSrc){const n=await g(()=>import("./pdf.worker-Dg1JjW3f.js"),[]);r.workerSrc=n.default}w=!0}return o}async function x(o){const n=(await h()).getDocument({data:new Uint8Array(o),disableFontFace:!0,useSystemFonts:!1}),s=await n.promise;try{const f=[];for(let a=1;a<=s.numPages;a+=1){const u=await s.getPage(a),y=await u.getTextContent();let e="",i=null,l=null,p=0,c=!1;for(const t of y.items){if(!("str"in t))continue;const d=t.transform[4],m=t.transform[5],_=Math.hypot(t.transform[2],t.transform[3])||10;!c&&l!==null&&i!==null&&(Math.abs(m-l)>_*T?e+=`
`:d-(i+p)>_*P&&(e+=" ")),e+=t.str,c=t.hasEOL===!0,c&&(e+=`
`),i=d,l=m,p=t.width??0}f.push(e),u.cleanup()}return{text:f.join(`

`).trim(),page_count:s.numPages}}finally{await n.destroy()}}export{x as extractTextFromPdf};
