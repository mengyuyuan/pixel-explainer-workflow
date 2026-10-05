/* Pixel rendering uses the generated sprites from claude-video-studio.
 * All animation states depend only on absolute time, including seek-backwards. */
const C={bg:'#101e2b',dark:'#142735',wall:'#223b49',line:'#355461',muted:'#78969e',paper:'#f4edda',gold:'#edb354',teal:'#65c9bd',td:'#33857e',red:'#e48a72',rd:'#9c554f',blue:'#50758b'};
const cv=document.querySelector('#art'),ctx=cv.getContext('2d');
const px=document.createElement('canvas');px.width=180;px.height=210;const p=px.getContext('2d');
const sprites={};for(const k of ['idle','blink','talk','cheer','walk1','walk2','point']){const i=new Image();i.src=`assets/hero-${k}.png`;sprites[k]=i}
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x)),ease=x=>{x=clamp(x);return x*x*(3-2*x)},ramp=(t,a,b)=>ease((t-a)/(b-a)),lerp=(a,b,k)=>a+(b-a)*k;
function rect(x,y,w,h,c){p.fillStyle=c;p.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h))}
function line(x,y,x2,y2,c,w=1){p.strokeStyle=c;p.lineWidth=w;p.beginPath();p.moveTo(Math.round(x),Math.round(y));p.lineTo(Math.round(x2),Math.round(y2));p.stroke()}
let labels=[];
function label(s,x,y,size=6,c=C.paper,align='left'){const m=p.getTransform();labels.push({s,x:m.a*x+m.c*y+m.e,y:m.b*x+m.d*y+m.f,size:size*m.a,c,align,alpha:p.globalAlpha})}
function text(s,x,y,size=32,c=C.paper,weight=600,align='left'){ctx.font=`${weight} ${size}px "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif`;ctx.textAlign=align;ctx.textBaseline='middle';ctx.fillStyle=c;ctx.fillText(s,x,y)}
function sprite(name,x,y,w=20){const i=sprites[name]||sprites.idle;if(i.complete&&i.naturalWidth)p.drawImage(i,Math.round(x),Math.round(y),w,w*1.5)}
function arrow(x,y,d,c){rect(x-1,y-8*d,2,14,c);for(let i=0;i<5;i++)rect(x-i,y+(5-i)*d,i*2+1,2,c)}
function pixelPlant(x,y){rect(x+4,y,7,10,C.rd);rect(x+3,y,9,2,C.red);line(x+7,y,x+7,y-19,C.td,2);rect(x,y-17,8,3,C.teal);rect(x+8,y-22,7,3,C.teal);rect(x+1,y-25,6,3,C.td)}
function lobby(t){
 rect(0,0,180,210,C.wall);rect(0,0,180,45,C.dark);
 for(let n=0;n<8;n++){rect(n*27-8,7,20,31,C.line);rect(n*27-5,10,14,23,C.blue);rect(n*27+2,10,1,23,C.dark)}
 rect(0,44,180,4,C.gold);rect(0,49,180,3,C.bg);
 for(let y=57;y<170;y+=13)for(let x=0;x<180;x+=24){rect(x+(y%2?0:12),y,22,1,'#2a4350')}
 rect(53,69,80,117,C.bg);rect(56,72,74,112,C.muted);rect(60,76,66,106,C.teal);rect(64,80,58,98,C.dark);
 rect(82,59,21,8,C.bg);label('01',92.5,63,6,C.gold,'center');
 const x=lerp(8,84,ramp(t,.45,2.6));const walk=t<2.6&&t>.45;
 sprite(walk?(Math.floor(t*7)%2?'walk1':'walk2'):'idle',x,144,20);
 const close=ramp(t,2.75,3.5);
 rect(64,80,29*close,98,C.teal);rect(122-29*close,80,29*close,98,C.td);
 if(close>.95)rect(92,80,1,97,C.dark);
 rect(136,106,9,18,C.bg);rect(139,110,3,3,C.gold);rect(139,118,3,3,C.line);
 rect(0,183,180,27,C.dark);for(let x=0;x<180;x+=24)line(x,184,x-12,210,C.wall);
 line(0,192,180,192,C.wall);line(0,203,180,203,C.wall);pixelPlant(22,182);pixelPlant(156,182);
 if(t>1.8&&t<3.1){label('↑',139,99,9,C.gold,'center')}
 if(t>3.55){rect(138,64,24,20,C.paper);rect(135,78,4,4,C.paper);label('?',150,74,12,C.dark,'center')}
}
function structure(t){
 rect(0,0,180,210,C.bg);rect(19,7,147,192,C.dark);
 for(let y=10;y<200;y+=12){rect(20,y,145,1,C.wall);for(let x=20;x<165;x+=24)rect(x+(Math.floor(y/12)%2)*12,y,1,12,C.wall)}
 // rails and floor landings remain visible throughout, providing a fixed spatial reference.
 rect(43,54,2,139,C.line);rect(105,54,2,139,C.line);rect(143,54,2,139,C.line);
 for(let y=75;y<200;y+=39){rect(0,y,39,4,C.blue);rect(0,y+4,39,2,C.wall);label(String(5-Math.round((y-75)/39)).padStart(2,'0'),8,y-7,7,C.muted)}
 rect(40,192,107,7,C.blue);for(let x=47;x<142;x+=8)rect(x,193,3,3,C.gold);
 let move=50*ramp(t,10.1,12.1)+15*ramp(t,21.4,23.2);
 const carY=135-move,weightY=65+move;
 const reveal=ramp(t,6.4,7.5),wReveal=ramp(t,8.25,9.3);
 // Upper semicircle: common cable runs from the left car over the sheave to right weight.
 p.strokeStyle=C.gold;p.lineWidth=1.6;p.beginPath();p.moveTo(78,carY);p.lineTo(78,38);p.arc(100,38,22,Math.PI,2*Math.PI);p.lineTo(122,weightY);p.stroke();
 const theta=move/22;
 p.fillStyle=C.blue;p.beginPath();p.arc(100,38,19,0,Math.PI*2);p.fill();
 p.strokeStyle=C.line;p.lineWidth=4;p.beginPath();p.arc(100,38,15,0,Math.PI*2);p.stroke();
 for(let a=0;a<4;a++){let u=theta+a*Math.PI/2;line(100,38,100+16*Math.cos(u),38+16*Math.sin(u),C.muted,2)}
 rect(97,35,6,6,C.gold);rect(115,31,24,4,C.blue);rect(136,19,25,23,C.gold);rect(139,22,19,17,'#bc823c');for(let i=0;i<4;i++)rect(142+i*4,24,2,13,C.gold);
 label('电机',148,12,7,C.gold,'center');
 p.globalAlpha=reveal;
 // Car: the orange character stays behind the moving door.
 rect(54,carY,48,49,C.teal);rect(57,carY+3,42,42,C.td);rect(60,carY+6,36,36,C.dark);rect(51,carY+6,3,6,C.blue);rect(102,carY+6,3,6,C.blue);
 sprite(t>26.3&&t<27.7?(Math.floor(t*7)%2?'walk1':'walk2'):(Math.floor(t*2)%7===0?'blink':'idle'),68-46*ramp(t,26.3,27.7),carY+18.5,17);
 // Doors remain closed during travel; front cutaway is schematic.
 const open=ramp(t,25.8,26.4);p.globalAlpha=reveal*.22;rect(60,carY+6,18*(1-open),36,C.teal);rect(96-18*(1-open),carY+6,18*(1-open),36,C.teal);p.globalAlpha=reveal;
 rect(57,carY+44,42,3,C.paper);label('轿厢',78,carY+56,7,C.teal,'center');
 p.globalAlpha=wReveal;rect(110,weightY,25,44,C.rd);rect(113,weightY+3,19,38,C.red);for(let n=0;n<5;n++){rect(113,weightY+4+n*7,19,1,'#f0b09a');rect(113,weightY+9+n*7,19,1,C.rd)}
 rect(110,weightY-3,25,3,C.gold);label('配重',123,weightY+52,7,C.red,'center');p.globalAlpha=1;
 if(t>=10.05&&t<12.65){arrow(51,carY+30,-1,C.teal);arrow(144,weightY+24,1,C.red)}
 return {carY,weightY,move};
}
function balance(t){
 labels=labels.filter(l=>!(l.x>=10&&l.x<=165&&l.y>=80&&l.y<=184));
 const intro=ramp(t,12.65,13.1),cancel=ramp(t,13.1,14.0);
 // A diagram of opposing gravitational contributions, not a calibrated mass ratio.
 p.globalAlpha=intro;rect(10,80,155,104,'#101e2beb');
 label('两侧重量，先抵消一部分',90,86,7,C.paper,'center');
 for(let i=0;i<6;i++){
  const paired=i<4;const u=paired?ramp(t,13.1+i*.2,13.65+i*.2):0;
  const x=paired?lerp(46,84,u):46,y=99+i*10;
  p.globalAlpha=intro*(paired?1-ramp(t,13.5+i*.2,14+i*.2):1);rect(x,y,17,7,C.teal);rect(x,y,17,1,C.paper);
 }
 for(let i=0;i<4;i++){
  const u=ramp(t,13.1+i*.2,13.65+i*.2);p.globalAlpha=intro*(1-ramp(t,13.5+i*.2,14+i*.2));rect(lerp(119,88,u),99+i*10,17,7,C.red);rect(lerp(119,88,u),99+i*10,17,1,'#f7bea8');
 }
 p.globalAlpha=intro;label('轿厢侧',53,169,6,C.teal,'center');label('配重侧',127,169,6,C.red,'center');
 if(t>14.55){line(67,153,99,153,C.gold);label('剩下的差值',103,150,6,C.gold);label('仍需电机处理',103,160,6,C.paper)}
 label('重量单位为示意，不代表实际比例',90,178,4.5,C.muted,'center');p.globalAlpha=1;
}
function motorDetail(t){
 const a=ramp(t,17.5,18.1)*(1-ramp(t,22.6,23.3));
 p.globalAlpha=a;rect(9,133,158,66,C.bg);labels=labels.filter(l=>l.y<133);
 label('电机仍需处理',90,141,8,C.paper,'center');
 const names=['重量差','摩擦','加速 / 减速'];const ats=[17.8,20.3,21.5];
 for(let i=0;i<3;i++){p.globalAlpha=a*ramp(t,ats[i],ats[i]+.3);rect(17+i*50,158,46,23,C.wall);label(names[i],40+i*50,169,6,i===0?C.teal:i===1?C.red:C.gold,'center')}
 p.globalAlpha=a;
 if(t>20.3&&t<21.6){for(let i=0;i<3;i++){line(92+i*2,61-i*3,97+i*2,57-i*3,C.red);}}
 if(t>21.5){label(t<22.4?'加速 ↗':'减速 ↘',65,116,7,C.gold,'center')}
 p.globalAlpha=1;
}
