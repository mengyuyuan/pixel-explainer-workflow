/* Original transparent pixel assets + frame-accurate scene acting. No reference video input. */
const out=document.querySelector('#art'),ctx=out.getContext('2d');
const stage=document.createElement('canvas');stage.width=960;stage.height=540;const p=stage.getContext('2d');
const C={paper:'#e7dfcc',ink:'#322b27',muted:'#887b66',line:'#c7baa1',red:'#a64f35',teal:'#386f69',gold:'#ba8338',ivory:'#fff5db',wood:'#83552d'};
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),lerp=(a,b,u)=>a+(b-a)*u;
const ease=x=>{x=clamp(x);return x*x*(3-2*x)},go=(t,a,b)=>ease((t-a)/(b-a));
const bounce=x=>{x=clamp(x);const z=x-1;return 1+2.7*z*z*z+1.7*z*z};
let labels=[];
const imgs={};for(const [key,file] of [['props','assets/props.png'],...PERFORMERS.map(a=>[a.key,a.file])]){imgs[key]=new Image();imgs[key].src=file}
function rect(x,y,w,h,col){p.fillStyle=col;p.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h))}
function stroke(x,y,xx,yy,col,w=1){p.strokeStyle=col;p.lineWidth=w;p.beginPath();p.moveTo(x,y);p.lineTo(xx,yy);p.stroke()}
function poly(points,col){p.fillStyle=col;p.beginPath();points.forEach(([x,y],i)=>i?p.lineTo(x,y):p.moveTo(x,y));p.closePath();p.fill()}
function text(s,x,y,size=20,col=C.ink,align='center',weight=800,outline=false){const m=p.getTransform();labels.push({s,x:m.a*x+m.c*y+m.e,y:m.b*x+m.d*y+m.f,size:size*Math.hypot(m.a,m.b),col,align,weight,alpha:p.globalAlpha,outline})}
function shadow(x,y,w=95){p.save();p.globalAlpha*=.15;p.fillStyle='#615240';p.beginPath();p.ellipse(x,y,w/2,5,0,0,Math.PI*2);p.fill();p.restore()}
function ground(y=442){stroke(45,y,915,y,'#b8aa92',1);for(let i=0;i<29;i++){let x=34+i*34;rect(x,y+8+(i%3)*3,14+i%9,1,'#cfc2aa')}}
function drawProp(i,x,y,w,alpha=1){if(!imgs.props.complete)return;const b=ATLAS.props[i],h=w*b[3]/b[2];p.save();p.globalAlpha*=alpha;p.drawImage(imgs.props,...b,Math.round(x-w/2),Math.round(y-h),Math.round(w),Math.round(h));p.restore();return h}
function actor(row,x,y,h,t,pose=0,flip=false){return perform(row,x,y,h,t,typeof pose==='string'?pose:['idle','surprise','reach','sad'][pose]||'idle',{flip})}
function cloth(x,y,w,progress=1,sway=0,maxH=0){const b=ATLAS.props[2],h=maxH||w*b[3]/b[2],pr=clamp(progress);if(pr<=0)return;
 for(let i=0;i<12;i++){const sw=b[2]/12,dw=w/12;let yy=Math.sin(i*.7+sway)*Math.min(2,Math.abs(sway));p.drawImage(imgs.props,b[0]+i*sw,b[1],sw,b[3]*pr,Math.round(x-w/2+i*dw),Math.round(y+yy),Math.ceil(dw),Math.round(h*pr))}
}
function loom(x,y,w,t,progress=.7,active=true){
 const h=drawProp(1,x,y,w)||w;const top=y-h;
 if(active){const z=Math.sin(t*12);rect(x-w*.27,top+h*.624+z*1.5,w*.54,4,'#946133');
  let sx=x+z*w*.22,sy=top+h*.66;poly([[sx-15,sy],[sx-11,sy-4],[sx+10,sy-4],[sx+16,sy],[sx+10,sy+4],[sx-11,sy+4]],'#422c1a');rect(sx-7,sy-2,14,3,'#ddc294')}
 cloth(x,top+h*.63,w*.45,progress,active?t*.7:0,h*.34);
}
function shop(x,y,w,name,col,alpha=1){p.save();p.globalAlpha*=alpha;shadow(x,y,w*.85);const h=drawProp(0,x,y,w)||w;text(name,x+4,y-h*.643,w*.049,'#f8e5b6');rect(x-w*.32,y-h*.48,5,14,col);p.restore()}
function clock(x,y,amount,t,scale=1){p.save();p.translate(x,y);p.scale(scale,scale);shadow(0,53,85);rect(-41,-42,82,85,'#524231');rect(-37,-38,74,77,'#b99161');rect(-33,-34,66,69,C.ivory);for(let i=0;i<12;i++){const a=i*Math.PI/6;rect(Math.sin(a)*27-1,-Math.cos(a)*27-1,3,3,C.ink)}const a=t*Math.PI*2;stroke(0,0,Math.sin(a)*24,-Math.cos(a)*24,C.red,3);stroke(0,0,18,-8,C.ink,3);rect(-2,-2,5,5,C.ink);text(amount+'小时',0,64,23,C.ink);p.restore()}
function bubble(s,x,y,w=150){rect(x-w/2,y-24,w,43,C.ink);rect(x-w/2+3,y-21,w-6,37,C.ivory);poly([[x-6,y+18],[x+7,y+18],[x-2,y+28]],C.ink);text(s,x,y-2,20,C.ink)}
function spark(x,y,t,col=C.gold){const u=go(t,0,.35),a=1-go(t,.42,.8);p.save();p.globalAlpha*=a;for(let i=0;i<8;i++){let ang=i*Math.PI/4;let r=17+u*26;rect(x+Math.cos(ang)*r-2,y+Math.sin(ang)*r-2,5,5,col)}p.restore()}
function bulb(x,y,t){const v=bounce(clamp(t/.28));p.save();p.translate(x,y);p.scale(v,v);rect(-10,-18,20,24,'#634329');rect(-16,-12,32,14,'#634329');rect(-8,-15,16,20,'#f9d86c');rect(-13,-9,26,10,'#f9d86c');rect(-6,7,12,5,'#7b6d59');rect(-4,12,8,4,'#413a31');p.restore();spark(x,y,t)}
function price(x,y,t,flip=false){const u=flip?go(t,5.9,6.25):0;let sc=flip?Math.cos(Math.PI*u):1;const value=u>.5?'× 2':'× 1';p.save();p.translate(x,y);p.rotate((flip&&t<6.8)?Math.sin((t-5.9)*22)*.08*(1-go(t,6.2,6.8)):0);stroke(0,-68,0,-32,C.wood,2);p.scale(Math.max(.045,Math.abs(sc)),1);poly([[-73,-34],[66,-34],[77,-23],[77,47],[-73,47]],'#79644d');poly([[-69,-30],[63,-30],[73,-21],[73,43],[-69,43]],C.ivory);rect(-58,-17,8,8,C.wood);text(value,10,5,45,u>.5?C.red:C.ink);p.restore()}
function stall(x,y,w,t){drawProp(3,x,y,w);const top=y-w*(ATLAS.props[3][3]/ATLAS.props[3][2]);return {top,counter:top+w*.535}}
function camera(z,x=480,y=270){p.translate(480,270);p.scale(z,z);p.translate(-x,-y)}
const paper=document.createElement('canvas');paper.width=960;paper.height=540;let pc=paper.getContext('2d');pc.fillStyle=C.paper;pc.fillRect(0,0,960,540);let seed=7251;for(let i=0;i<7200;i++){seed=(seed*1664525+1013904223)>>>0;let x=seed%960;seed=(seed*1664525+1013904223)>>>0;let y=seed%540;pc.fillStyle=i%2?'rgba(91,67,35,.035)':'rgba(255,251,229,.08)';pc.fillRect(x,y,1+i%2,1)}
function drawFrame(t){
 p.setTransform(1,0,0,1,0,0);p.globalAlpha=1;p.imageSmoothingEnabled=false;p.clearRect(0,0,960,540);p.drawImage(paper,0,0);labels=[];
 text(FILM.series||FILM.title,36,29,15,'#8b806d','left',600);text(FILM.subtitle||'',925,29,14,'#8b806d','right',600);
 p.save();p.beginPath();p.rect(0,52,960,427);p.clip();if(window.assetsReady)scene(t);p.restore();
 const cue=FILM.cues.find(x=>t>=x.start&&t<x.end);if(cue)text(cue.text.replace(/[。；]$/,''),480,506,25,'#fff9ed','center',800,true);
 rect(38,534,884,1,'#d0c3ac');rect(38,534,884*clamp(t/FILM.duration),1,'#ab8c5c');
 ctx.setTransform(1,0,0,1,0,0);ctx.imageSmoothingEnabled=false;ctx.clearRect(0,0,out.width,out.height);ctx.fillStyle=C.paper;ctx.fillRect(0,0,out.width,out.height);const zoom=Math.min(out.width/960,out.height/540),ox=(out.width-960*zoom)/2,oy=(out.height-540*zoom)/2;ctx.setTransform(zoom,0,0,zoom,ox,oy);ctx.drawImage(stage,0,0);
 for(const l of labels){ctx.save();ctx.globalAlpha=l.alpha;ctx.font=`${l.weight} ${l.size}px "Microsoft YaHei",sans-serif`;ctx.textAlign=l.align;ctx.textBaseline='middle';if(l.outline){ctx.strokeStyle='#3e372e';ctx.lineWidth=3.5;ctx.lineJoin='round';ctx.strokeText(l.s,l.x,l.y)}ctx.fillStyle=l.col;ctx.fillText(l.s,l.x,l.y);ctx.restore()}
}
window.drawFrame=drawFrame;let now=0;const state={};Object.defineProperty(state,'time',{get:()=>now,set:v=>{now=v;drawFrame(v)}});
const tl=gsap.timeline({paused:true});tl.to(state,{time:FILM.duration,duration:FILM.duration,ease:'none'},0);window.__timelines['pixel-story']=tl;
window.assetsLoaded=Promise.all(Object.values(imgs).map(i=>i.decode())).then(()=>{window.assetsReady=true;drawFrame(now)});drawFrame(0);
