import pathlib,json
from settings import load_config
p=pathlib.Path(__file__).parent
config=load_config()
rate=config['playbackRate']
duration=30/rate
source=(p/'scene-core.js').read_text(encoding='utf-8')
source=source.replace('px.width=180','px.width=480')
source=source.replace(" labels=labels.filter(l=>!(l.x>=10&&l.x<=165&&l.y>=80&&l.y<=184));",'')
source=source.replace(";labels=labels.filter(l=>l.y<133)",'')
source+=r'''
function wideBuilding(t,mode){
 rect(0,0,480,210,mode==='lobby'?C.wall:C.bg);
 if(mode==='lobby'){
  rect(0,0,480,45,C.dark);
  for(let n=0;n<19;n++){rect(n*27-8,7,20,31,C.line);rect(n*27-5,10,14,23,C.blue);rect(n*27+2,10,1,23,C.dark)}
  rect(0,44,480,4,C.gold);rect(0,49,480,3,C.bg);
  for(let y=57;y<182;y+=13)for(let x=0;x<480;x+=24)rect(x+(y%2?0:12),y,22,1,'#2a4350');
  rect(0,183,480,27,C.dark);for(let x=0;x<480;x+=24)line(x,184,x-12,210,C.wall);line(0,192,480,192,C.wall);line(0,203,480,203,C.wall);
  // Wider environment is actual scene art, not a portrait frame with side bars.
  rect(40,94,63,47,C.dark);rect(44,98,55,39,C.blue);rect(70,98,2,39,C.wall);rect(44,116,55,2,C.wall);
  rect(46,159,60,6,C.gold);rect(47,166,4,18,C.rd);rect(99,166,4,18,C.rd);rect(46,146,60,10,C.rd);pixelPlant(120,182);
  rect(368,106,50,61,C.dark);rect(372,110,42,52,C.wall);label('ELEVATOR',393,125,6,C.gold,'center');label('↑  ↓',393,147,12,C.teal,'center');pixelPlant(441,182);
 }else{
  // Outer floors provide a continuous building context around the shaft.
  for(let y=36;y<210;y+=39){
   rect(0,y,480,2,'#1d3341');
   for(let x=0;x<480;x+=56){rect(x+7,y-24,32,14,'#1b303e');rect(x+7,y-24,32,2,'#284352')}
  }
 }
}
function draw(t){
 ctx.clearRect(0,0,1920,1080);ctx.fillStyle=C.bg;ctx.fillRect(0,0,1920,1080);
 const title=t<4.5?'你坐电梯时':t<6.4?'藏在井道里的搭档':t<12.6?'一上一下，互相帮忙':t<17.5?'重量，先抵消一部分':t<23.3?'电机还要做什么？':'多一块重物，反而省力';
 ctx.fillStyle=C.gold;ctx.fillRect(50,43,13,13);text('像素里的原理',80,49,26,C.muted,500);
 text(title,960,57,48,C.paper,700,'center');text('01',1865,49,26,C.gold,600,'right');
 ctx.fillStyle=C.line;ctx.fillRect(50,112,1820,2);
 labels=[];p.setTransform(1,0,0,1,0,0);p.globalAlpha=1;p.clearRect(0,0,480,210);p.imageSmoothingEnabled=false;
 wideBuilding(t,t<4.5?'lobby':'shaft');
 if(t<4.5){p.save();p.translate(150,0);lobby(t);p.restore()}
 else if(t<6.4){
  label('真实的钢索与导轨',92,64,10,C.paper,'center');label('进入井道内部',92,82,7,C.muted,'center');
  label('接下来，拆开看',388,130,9,C.gold,'center');
  // Pixel rope traces introduce the next shot while the real source remains visible.
  line(357,55,357,107,C.gold,2);line(417,55,417,147,C.gold,2);rect(344,107,26,30,C.teal);rect(408,147,18,23,C.red);
 }else{
  const spread=ramp(t,12.55,13.15)*(1-ramp(t,22.6,23.3));const origin=lerp(150,264,spread);
  const zMix=ramp(t,17.5,18.25)*(1-ramp(t,22.6,23.3)),z=1+.40*zMix;
  p.save();p.translate(origin+90,85);p.scale(z,z);p.translate(-lerp(90,116,zMix),-lerp(85,68,zMix));structure(t);p.restore();
  if(t>=12.6&&t<17.5){p.save();p.translate(36,0);balance(t);p.restore();label('同一套系统',246,41,7,C.muted,'center')}
  if(t>=17.5&&t<23.3){p.save();p.translate(38,-43);motorDetail(t);p.restore();label('重量差仍然存在',126,56,10,C.teal,'center');label('电机控制运动',126,74,8,C.muted,'center')}
  if(t>=6.4&&t<12.6){label('曳引式电梯',75,68,12,C.paper,'center');label('钢索连接两端',75,88,8,C.muted,'center');if(t>=10.1){label('↑  轿厢上',391,99,10,C.teal,'center');label('↓  配重下',391,120,10,C.red,'center')}}
  if(t>=23.3){label('隐藏搭档',74,80,13,C.paper,'center');label('配重',74,103,18,C.red,'center');label('先平衡，再驱动',397,106,10,C.gold,'center')}
 }
 ctx.imageSmoothingEnabled=false;ctx.drawImage(px,0,126,1920,840);
 ctx.save();ctx.beginPath();ctx.rect(0,126,1920,840);ctx.clip();for(const l of labels){ctx.globalAlpha=l.alpha;text(l.s,l.x*4,126+l.y*4,l.size*4,l.c,600,l.align)}ctx.restore();
 let cue=TIMING.cues.find(x=>t>=x.start&&t<x.end+.16);
 if(cue){ctx.fillStyle='#0b1723';ctx.fillRect(300,971,1320,73);text(cue.text,960,1009,38,C.paper,600,'center')}
 if(t>27){text('原理：Otis  ·  实拍：Uwe Brodrecht / CC BY-SA 2.0（剪裁）',960,1007,24,C.muted,500,'center')}
 ctx.fillStyle=C.line;ctx.fillRect(50,1063,1820,3);ctx.fillStyle=C.gold;ctx.fillRect(50,1063,1820*clamp(t/30),3);
}
window.drawFrame=draw;
let current=0;const state={};Object.defineProperty(state,'time',{get:()=>current,set:v=>{current=v;draw(v)}});
const timeline=gsap.timeline({paused:true});timeline.to(state,{time:30,duration:25,ease:'none'},0);
window.__timelines=window.__timelines||{};window.__timelines['pixel-elevator-wide']=timeline;
Promise.all(Object.values(sprites).map(i=>i.decode())).then(()=>draw(current));draw(0);
'''
source=source.replace('time:30,duration:25',f'time:30,duration:{duration}')
(p/'landscape.js').write_text(source,encoding='utf-8')
(p/'timing.js').write_text('window.TIMING='+json.dumps(json.loads((p/'timing.json').read_text(encoding='utf-8')),ensure_ascii=False)+';',encoding='utf-8')
html='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>电梯的隐藏搭档 · 横版</title><script src="node_modules/gsap/dist/gsap.min.js"></script>
<style>*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#101e2b}#root{position:relative;width:1920px;height:1080px;overflow:hidden}canvas{position:absolute;inset:0;width:1920px;height:1080px}#shaft{position:absolute;left:744px;top:166px;width:432px;height:768px;object-fit:cover;z-index:1}#credit{position:absolute;left:748px;top:901px;color:#fff;font:17px 'Microsoft YaHei';z-index:2;background:#14222bcc;padding:5px 8px}audio{display:none}</style></head><body>
<div id="root" data-composition-id="pixel-elevator-wide" data-start="0" data-duration="25" data-width="1920" data-height="1080" data-fps="30">
<canvas id="art" width="1920" height="1080"></canvas>
<video id="shaft" class="clip" data-start="3.75" data-duration="1.583333333" data-track-index="1" data-media-start="0" muted src="assets/shaft-excerpt.mp4"></video>
<div id="credit" class="clip" data-start="3.75" data-duration="1.583333333" data-track-index="2">实拍：Uwe Brodrecht · CC BY-SA 2.0</div>
<audio id="narration-and-foley-wide" class="clip" data-start="0" data-duration="25" data-track-index="3" src="build/mix.wav"></audio>
</div><script>window.__timelines=window.__timelines||{};</script><script src="timing.js"></script><script src="landscape.js"></script></body></html>'''
html=html.replace('data-duration="25"',f'data-duration="{duration}"').replace('data-start="3.75"',f'data-start="{4.5/rate}"').replace('data-duration="1.583333333"',f'data-duration="{1.9/rate}"')
(p/'index.html').write_text(html,encoding='utf-8')
print(f'1920x1080; {duration:g} seconds; animation rate {rate:g}')
