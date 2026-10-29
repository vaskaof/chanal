const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1400}});
await p.goto('file://'+process.cwd()+'/cards.html');await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(500);
for(let i=1;i<=10;i++){const id='c'+String(i).padStart(2,'0');await p.locator('#'+id).screenshot({path:`out/knopka-${id}.png`});}
await b.close();})();
