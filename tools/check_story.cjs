/* Render representative authored frames and verify absolute-time seeking. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path');
(async()=>{
 const dir=path.resolve(process.argv[2]||''),conf=JSON.parse(fs.readFileSync(path.join(dir,'project.json'),'utf8'));
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
 const page=await browser.newPage({viewport:{width:conf.width,height:conf.height}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.goto('file:///'+path.join(dir,'index.html').replace(/\\/g,'/'));await page.evaluate(()=>window.assetsLoaded);
 const intervals=conf.shots||conf.cues;const times=intervals.flatMap(s=>[.15,.5,.85].map(u=>s.start+(s.end-s.start)*u));
 const frames=path.join(dir,'build/check-frames');fs.mkdirSync(frames,{recursive:true});
 for(let i=0;i<times.length;i++){await page.evaluate(t=>window.drawFrame(t),times[i]);await page.screenshot({path:path.join(frames,`${String(i).padStart(2,'0')}.png`)});}
 const t=times[Math.floor(times.length/2)];await page.evaluate(t=>window.drawFrame(t),t);const a=await page.screenshot();await page.evaluate(()=>window.drawFrame(0));await page.evaluate(t=>window.drawFrame(t),t);const b=await page.screenshot();
 const result={errors,seekDeterministic:a.equals(b),times,normalSpeedReview:'unverified',listening:'unverified'};
 fs.writeFileSync(path.join(dir,'build/browser-check.json'),JSON.stringify(result,null,2));await browser.close();console.log(JSON.stringify(result));if(errors.length||!a.equals(b))process.exitCode=1;
})();
