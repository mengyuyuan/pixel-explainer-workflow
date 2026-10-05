function calendar(t){const u=t-12.867;shadow(480,443,220);rect(362,127,234,292,'#7c6650');rect(352,115,234,292,C.ivory);rect(352,115,234,47,C.red);for(let i=0;i<5;i++)rect(375+i*40,99,8,32,'#655646');text('三天前',469,267,49,C.ink);if(u<.6){p.save();const z=go(u,0,.6);p.globalAlpha=1-z;p.translate(469,161);p.rotate(-z*1.1);rect(-113,0,226,242,'#f4ead4');text('今天',0,100,50,C.ink);p.restore()}text('回到像素镇',469,365,19,C.muted)}
function equalCloths(t,lo=21.697,hi=22.6){let u=go(t,lo,hi);ground();cloth(lerp(268,374,u),155,185,1);cloth(lerp(692,586,u),155,185,1);heldCloth(perform(0,143,441,128,t,'carry'),69);heldCloth(perform(1,817,441,128,t,'carry',{flip:true}),69);if(u>.9){stroke(282,350,678,350,'#9a8b70',2);stroke(282,343,282,357,'#9a8b70',2);stroke(678,343,678,357,'#9a8b70',2);text('同样的规格 · 同样的质量',480,112,30,C.teal)}}
function scene(t){
 if(t>=37.6){later(t);return;}
 if(t<2.03){
  ground();shop(679,440,337,'阿成布坊',C.red);perform(0,329,442,224,t,t>.38?'surprise':'think');if(t>.4)bulb(349,144,t-.4);if(t>.85)bubble('有办法了！',519,178,164);
 }else if(t<5.87){
  ground();operatedLoom(1,338,440,242,t-2.03,go(t,2.1,4.05),t<4.05,{height:128});operatedLoom(0,744,440,242,t-2.03,go(t,2.1,5.62),t<5.62,{rate:.53,height:128});
  if(t>=3.17)clock(338,121,2,Math.min(1,(t-3.17)/.75),.67);if(t>=4.35)clock(744,121,4,Math.min(2,(t-4.35)/.62),.67);text('同样一匹布',480,69,27,C.muted);
 }else if(t<10.03){
  ground();camera(lerp(1.12,1,go(t,9.1,10.03)),480,281);perform(0,278,438,190,t,t>7.43&&t<8.87?'speak':'reach');const st=stall(608,443,360,t);cloth(588,st.counter-12,152,1);price(727,234,t,true);
  if(t>7.43)bubble('多干两小时！',285,188,183);if(t>8.87)text('要价翻倍',582,108,34,C.red);
 }else if(t<12.867){
  ground();stall(238,440,296,t);stall(715,440,296,t);cloth(230,336,113);cloth(708,336,113);
  perform(0,83,441,128,t,t>11.05?'sad':'idle');perform(1,877,441,128,t,'idle',{flip:true});text('×2',362,292,20,C.red);text('×1',839,292,20,C.teal);
  if(t<10.42){let a=perform(2,454,442,128,t,'inspect',{flip:true});heldCloth(a,43)}
  else if(t<10.72)perform(2,454,442,128,t,'refuse',{flip:true});
  else if(t<10.92)perform(2,454,442,128,t,'turn');
  else moveActor(2,454,587,442,128,t,10.92,12.25,'nod');
  if(t<10.53)text('？',470,269,36,C.red);if(t>11.5){for(let i=0;i<3;i++)rect(105+i*9,312+(i%2)*4,3,11,'#827b9b')}
 }else if(t<14.897){calendar(t);
 }else if(t<19.237){
  ground();let v=go(t,14.897,15.4);shop(269,442,316*v,'阿成布坊',C.red);shop(690,442,316*v,'阿明布坊',C.teal);
  moveActor(0,320,401,443,87,t,16.637,17.22,'nod');moveActor(1,746,818,443,87,t,18.157,18.65,'nod');text('像素镇',480,89,31,C.ink);
 }else if(t<21.697){
  ground();operatedLoom(0,338,440,264,t-19.237,.55,true,{phase:.1});operatedLoom(1,744,440,264,t-19.237,.55,true,{phase:.35});text(t<20.617?'同样的工具':'相近的手艺',480,90,33,C.ink);
 }else if(t<24.433){equalCloths(t);
 }else if(t<27.583){
  ground();shop(181,440,210,'阿成布坊',C.red,.25);shop(786,440,210,'阿明布坊',C.teal,.25);operatedLoom(0,510,439,300,t,.5,false,{height:192,rest:'reach'});text(t<25.883?'先把问题讲简单':'原料、工具等条件不变',480,84,29,C.ink);
 }else if(t<32.903){
  ground();const pr=go(t,27.9,32.1);operatedLoom(1,619,439,302,t-27.583,pr,t<32.15,{height:192});clock(210,228,2,Math.max(0,Math.min(2,(t-29.463)/1.5)),1.15);text('只看织布这一道工序',540,87,30,C.ink);if(t>32.15)spark(570,373,t-32.15,C.teal);
 }else{
  ground();stall(665,442,341,t);cloth(680,319,93);perform(0,235,443,192,t,t>34.443?'sad':'idle');let a=perform(2,473,443,192,t,t<33.3?'reach':t<35.8?'inspect':'nod');if(t>=33.3&&t<35.8)heldCloth(a,60);
  text('交换时，看的还是这匹布',536,108,29,C.ink);
 }
}
function crossAt(x,y,r=15){stroke(x-r,y-r,x+r,y+r,C.red,5);stroke(x-r,y+r,x+r,y-r,C.red,5)}
function cog(x,y,r,t,col='#bb914d'){
 p.save();p.translate(x,y);p.rotate(t);for(let i=0;i<12;i++){p.rotate(Math.PI/6);rect(-r*.16,-r*1.15,r*.32,r*.48,'#5d4932');rect(-r*.11,-r*1.10,r*.22,r*.36,col)}
 p.fillStyle='#604933';p.beginPath();p.arc(0,0,r,0,Math.PI*2);p.fill();p.fillStyle=col;p.beginPath();p.arc(0,0,r*.87,0,Math.PI*2);p.fill();p.fillStyle='#765b38';p.beginPath();p.arc(0,0,r*.57,0,Math.PI*2);p.fill();
 for(let i=0;i<4;i++){p.rotate(Math.PI/2);rect(-2,-r*.66,4,r*.66,col)}rect(-4,-4,8,8,'#dbbe84');p.restore();
}
function powered(x,y,w,t,progress=.75,on=true){loom(x,y,w,t*(on?1.8:0),progress,on);let h=w*ATLAS.props[1][3]/ATLAS.props[1][2],xx=x-w*.33,yy=y-w*.277;
 cog(xx,yy,w*.09,on?t*3.8:0);cog(xx+w*.13,yy+w*.1,w*.055,on?-t*6.2:0);stroke(xx,yy,x+w*.18*Math.sin((on?t:0)*21.6),y-h*.355,'#756f5e',3);rect(xx-4,yy-4,8,8,'#d0c19c');
}
function tag(s,x,y,w=126,col=C.ink){poly([[x-w/2,y-21],[x+w/2-10,y-21],[x+w/2,y-11],[x+w/2,y+25],[x-w/2,y+25]],'#80674c');rect(x-w/2+3,y-18,w-7,39,C.ivory);text(s,x,y+1,26,col)}
function rulerAt(x,y,n=2,u=0){let w=lerp(240,120,u);rect(x-w/2-3,y-3,w+6,36,'#725536');rect(x-w/2,y,w,30,'#dfb96e');for(let i=0;i<=w;i+=12)rect(x-w/2+i,y,1,i%60===0?12:6,'#755738');text(n+'小时',x,y+21,17,'#503b29');text('通常生产条件下的社会尺度',x,y+53,19,C.muted)}
function tinyLooms(t,upgrades=0,y=333){for(let i=0;i<6;i++){const x=106+i*151;operatedLoom(i===0?1:0,x,y,96,t+i*.39,.75,true,{height:64,powered:i<upgrades,rate:i<upgrades?1.6:1,phase:i*.17});text(i<upgrades?'1小时':'2小时',x,y+26,18,i<upgrades?C.teal:C.muted)}}
function arrowAt(x,y,xx,yy,col=C.gold){stroke(x,y,xx,yy,col,3);const a=Math.atan2(yy-y,xx-x);poly([[xx,yy],[xx-12*Math.cos(a-.5),yy-12*Math.sin(a-.5)],[xx-12*Math.cos(a+.5),yy-12*Math.sin(a+.5)]],col)}
function later(t){
 const s=FILM.shots.find(s=>t>=s.start&&t<s.end)||FILM.shots.at(-1),u=clamp((t-s.start)/(s.end-s.start)),local=t-s.start;
 const q=(a,b)=>ease((u-a)/(b-a));ground();
 switch(s.kind){
 case 'slow':{
  if(u<.56){operatedLoom(0,470,439,306,local,q(.13,.52),u<.50,{height:192,rate:.43});clock(767,236,4,q(.13,.50)*2,.93);text('同样的活，故意做慢',480,81,30,C.ink)}
  else{stall(605,441,356,t);cloth(579,322,144);perform(0,279,442,192,t,u>.66&&u<.87?'speak':'reach');tag('× 2',746,245,133,C.red);if(u>.66)bubble('两倍时间，两倍价？',451,154,244)}
  break;
 }
 case 'market':{
  stall(270,442,265,t);stall(747,442,265,t);cloth(750,347,82);rect(304,423,85,7,C.wood);rect(311,430,6,13,C.wood);rect(378,430,6,13,C.wood);perform(0,100,442,128,t,u>.34?'sad':'idle');perform(1,897,442,128,t,'idle',{flip:true});
  let a;
  if(u<.09)a=perform(2,415,443,192,t,'reach',{flip:true});
  else if(u<.25){a=perform(2,415,443,192,t,'inspect',{flip:true});heldCloth(a,65)}
  else if(u<.31){a=perform(2,415,443,192,t,'place',{flip:true});heldCloth(a,65)}
  else if(u<.38)perform(2,415,443,192,t,'refuse',{flip:true});
  else if(u<.415)perform(2,415,443,192,t,'turn');
  else a=moveActor(2,415,591,443,192,u,.415,.64,u>.70?'nod':'inspect');
  if(u<.09||u>=.31){rect(306,407,67,16,'#d6c29a');for(let j=0;j<67;j+=6)rect(306+j,409,2,12,'#b8a478')}
  if(u>.70){clock(223,184,4,0,.61);clock(747,184,2,0,.61);crossAt(361,185,14);text('多出的耗时，没有变成更多的布',480,86,28,C.red)}else text(u<.31?'摸一摸，再比一比':u<.415?'同样的布，为什么贵一倍？':'转身，去另一家',480,100,29,C.ink);
  break;
 }
 case 'social':{
  text('社会必要劳动时间',480,90,34,C.ink);
  if(u<.28){operatedLoom(0,527,437,284,local,.6,true,{height:192});text('从一间布坊看出去',480,461,19,C.muted)}
  else{tinyLooms(t,0,325);rulerAt(480,389,2,0);if(u>.68)text('通常的工具 · 一般的熟练程度 · 一般的劳动强度',480,152,21,C.teal)}
  break;
 }
 case 'ruler':{
  if(u<.30){clock(390,243,4,local*.2,1.4);actor(0,600,440,151,t,2,true);if(u>.12)crossAt(390,240,50);text('不是个人的秒表',480,87,32,C.ink)}
  else if(u<.60){shop(485,438,292,'布坊',C.wood);actor(2,276,440,138,t,2);tag('规定 2 小时',480,162,185,C.ink);crossAt(480,161,28);text('也不是谁拍板规定',480,84,30,C.ink)}
  else{tinyLooms(t,0,326);rulerAt(480,390,2,0);text('看同类商品的通常生产条件',480,90,30,C.teal);if(u<.8)text('不是把所有耗时随意平均',480,148,21,C.muted)}
  break;
 }
 case 'upgrade':{
  if(u<.55){
   shop(145,441,210,'阿明布坊',C.teal,.32);if(u>.43)powered(649,440,282,local,q(.43,.55),true);else loom(649,440,282,t,.35,false);let a;
   if(u<.09){a=perform(1,384,442,192,t,u<.035?'reach':'place');cog(a.right[0],a.right[1]+5,27,0);a.hands()}
   else if(u<.25){a=moveActor(1,384,476,442,192,u,.10,.24,'carry',false,true);heldGear(a)}
   else if(u<.34){a=perform(1,476,442,192,t,'push');let v=q(.25,.32);cog(lerp(a.right[0],556,v),lerp(a.right[1],362,v),27,0);a.hands()}
   else{if(u<=.43)cog(556,362,27,0);a=perform(1,466,442,192,t,u<.40?'nod':u<.43?'reach':'work');if(u>=.40){stroke(552,377,a.right[0],a.right[1],C.wood,5);a.hands()}}
   text(u<.32?'第二天，装上新传动装置':'装好，试一试',480,87,30,C.ink);
  }else{operatedLoom(0,324,440,232,local,.72,true,{height:128});operatedLoom(1,744,440,245,local,q(.55,.76),u<.8,{height:128,powered:true,rate:1.6});clock(324,138,2,0,.70);clock(744,138,1,q(.55,.76),.70);if(u>.80)bubble('全镇立刻减半？',480,212,195)}
  break;
 }
 case 'mechanism':{
  if(u<.65){operatedLoom(1,563,443,309,local,q(.10,.6),true,{height:192,powered:true,rate:1.6});cog(199,263,44,local*3.8);cog(257,311,27,-local*6.2);arrowAt(279,330,342,353);text('传动接过去，梭子更快了',480,84,30,C.ink)}
  else{operatedLoom(1,291,440,247,local,.86,false,{height:128,powered:true});for(let i=0;i<3;i++)operatedLoom(0,583+i*130,402,95,local+i*.3,.7,true,{height:64});text('一家先换机',263,129,30,C.teal);text('其余仍用旧织机',695,182,26,C.muted);text('≠',478,307,51,C.red)}
  break;
 }
 case 'advantage':{
  tinyLooms(t,1,350);text('阿明先快了，同行还没变',480,86,31,C.ink);cloth(67,184,49);cloth(122,184,49);for(let i=1;i<6;i++)cloth(93+i*155,202,42);
  rulerAt(515,392,2,0);if(u>.55){rect(33,392,135,35,C.teal);text('个别优势',101,409,19,C.ivory)}
  break;
 }
 case 'spread':{
  const n=Math.min(6,1+Math.floor(q(.10,.64)*5.99));tinyLooms(t,n,344);text('新机器，陆续普及',480,82,32,C.ink);for(let i=0;i<n;i++)cog(93+i*155,174,17,t*2.6);
  let v=q(.70,.86);rulerAt(480,395,v>.65?1:2,v);if(v>.8)text('1小时，成为新的通常水平',480,139,25,C.teal);
  break;
 }
 case 'old':{
  operatedLoom(0,324,438,246,local,q(.12,.56),u<.56,{height:128,rest:u>.62?'sad':'carry'});operatedLoom(1,744,438,239,local,q(.12,.36),u<.36,{height:128,powered:true,rate:1.6});
  clock(282,138,2,q(.1,.54),.69);clock(692,138,1,q(.1,.34),.69);
  if(u>.60){rect(376,224,200,56,C.ivory);text('新的社会尺度',476,241,19,C.muted);text('1 小时',476,265,24,C.teal);arrowAt(358,329,439,297,C.red)}else text('阿成没偷懒，生产条件变了',480,81,29,C.ink);
  break;
 }
 case 'productivity':{
  const v=q(.23,.57);text('同样两小时，产出更多布',480,86,31,C.ink);rect(242,157,476,31,'#dec08b');for(let i=0;i<=20;i++)rect(242+i*23.8,157,1,i%5===0?12:6,'#795b36');text('2 小时',480,176,20,C.ink);
  cloth(lerp(480,328,v),264,162);if(v>0){p.save();p.globalAlpha=v;cloth(640,264,162);p.restore()}
  if(v>.9){stroke(480,157,480,191,C.ink,2);arrowAt(348,197,328,244);arrowAt(612,197,640,244);text('1 小时',328,235,23,C.teal);text('1 小时',640,235,23,C.teal)}else arrowAt(480,198,480,245);
  text('比较同类商品，原料等其他条件不变',480,461,20,C.muted);break;
 }
 case 'quality':{
  const v=q(.15,.55);cloth(253,195,202);cloth(727,195,202);let a=perform(0,473,440,192,t,u<.15?'inspect':u<.55?(Math.floor(local*4)%2?'push':'pull'):'inspect');
  if(u<.15||u>=.55)heldCloth(a,59);
  else{const hx=a.right[0],hy=a.right[1];cloth(573,hy+6,100,1,0,68);stroke(hx,hy,hx+10,hy+15,C.ink,2);stroke(hx+10,hy+15,589,hy+32,C.red,1);a.hands()}
  p.save();p.beginPath();p.rect(626,194,202,210);p.clip();for(let i=0;i<15*v;i++){let x=653+(i%3)*60,y=228+Math.floor(i/3)*32;poly([[x,y-7],[x+7,y],[x,y+7],[x-7,y]],C.red);rect(x+7,y+1,14,3,C.teal)}p.restore();
  text('普通布',253,156,28,C.ink);text('更结实 / 绣花布',727,156,28,C.red);text(u>.56?'对象不同，不能硬套同一个比较':'如果材料、工艺、用途变了呢？',480,83,29,C.ink);
  if(u>.56)text('≠',477,189,43,C.red);break;
 }
 case 'price':{
  const st=stall(295,440,310,t);cloth(275,324,122);perform(1,117,442,128,t,u>.5?'nod':'idle');
  for(let i=0;i<5;i++)moveActor(2,1008+i*65,503+i*82,442,128,u,.12+i*.055,.38+i*.055,i===0?'reach':'idle',true);
  text('价值 ≠ 每天的成交价格',480,84,31,C.ink);if(u>.31){tag('售价 ↑',315,178,148,C.red)}else tag('售价',315,178,148);
  clock(760,197,2,0,.76);text('生产条件没有变',755,285,23,C.teal);if(u>.47)text('赶集的人多了',624,132,23,C.muted);
  break;
 }
 case 'decision':{
  shop(252,441,311,'阿成布坊',C.red);shop(701,441,311,'阿明布坊',C.teal);let a;
  if(u<.23){a=perform(0,389,443,128,t,u<.08?'reach':'carry');heldPaper(a,'×2')}
  else if(u<.27)perform(0,389,443,128,t,'turn',{flip:true});
  else{a=moveActor(0,389,568,443,128,u,.27,.67,u>.76&&u<.85?'speak':'carry',false,true);heldPaper(a)}
  perform(1,822,442,128,t,u>.85&&u<.94?'speak':u>.70?'nod':'idle',{flip:true});
  text(u<.3?'收起翻倍价签':'看产品，也看同行怎样生产',480,86,31,C.ink);break;
 }
 case 'recap':{
  if(u<.35){perform(0,294,440,192,t,'think');cloth(659,230,187);text('这把尺，不给人的辛苦和人格打分',480,88,29,C.ink);rulerAt(664,382,2,0)}
  else{const v=q(.68,.9);tinyLooms(t,v>.5?6:0,340);rulerAt(480,393,v>.5?1:2,v);text(u<.66?'多耗时间，不自动更值钱':'普遍提高效率，社会尺度才改变',480,86,29,C.ink)}
  break;
 }
 case 'end':{
  if(u<.52){shop(654,441,368,'布厂招工',C.teal);moveActor(0,92,384,444,128,u,.01,.25,u>.29&&u<.43?'speak':'idle');perform(2,816,443,128,t,u>.43?'nod':'idle',{flip:true});if(u>.29)bubble('一天多少钱？',455,234,191)}
  else{perform(0,271,443,192,t,u>.72?'think':'inspect');perform(2,767,443,192,t,u>.55&&u<.65?'speak':'nod',{flip:true});rect(377,239,220,142,'#806c51');rect(369,230,220,142,C.ivory);text('招 工',479,257,27,C.ink);stroke(389,284,568,284,C.line,1);text('劳动   /   劳动力',478,319,26,C.ink);if(u>.8)text('下一集，接着讲',480,108,33,C.teal)}
  break;
 }
 }
function heldGear(a){cog((a.right[0]+a.left[0])/2,(a.right[1]+a.left[1])/2+5,27,0);a.hands()}
}
