/* Replace these five action demonstrations with your story. Logical stage 960×540.
   Most figures are 64 px tall (~12% of frame); only contact detail uses 128 px. */
function cog(x,y,r,t){p.save();p.translate(x,y);p.rotate(t);for(let i=0;i<10;i++){p.rotate(Math.PI/5);rect(-r*.2,-r*1.13,r*.4,r*.45,C.wood)}for(const [radius,col] of [[r,'#5d4932'],[r*.87,'#bb914d'],[r*.60,'#765b38']]){p.fillStyle=col;p.beginPath();p.arc(0,0,radius,0,Math.PI*2);p.fill()}for(let i=0;i<4;i++){p.rotate(Math.PI/2);rect(-2,-r*.72,4,r*.72,'#bb914d')}rect(-3,-3,6,6,C.ivory);p.restore()}
function powered(x,y,w,t,progress=.75,on=true){loom(x,y,w,t,progress,on);if(on)cog(x-w*.3,y-w*.2,w*.1,t*4)}
function scene(t){
 ground();
 if(t<6){
  shop(206,442,267,'工作间',C.red);operatedLoom(0,566,442,151,t,go(t,.4,4.5),t<4.5,{height:64});perform(1,797,442,64,t,'idle',{flip:true});
  text('接触工具 → 操作 → 拿起成品',490,138,22,C.muted);
 }else if(t<12){
  shop(170,442,249,'工作间',C.red);stall(765,442,260,t);
  const a=moveActor(0,307,643,442,64,t,6.2,9.6,'carry',false,true);heldCloth(a,28);perform(2,886,442,64,t,t>9.6?'nod':'idle',{flip:true});
  text('用位移控制步态，到达后停止',480,137,22,C.muted);
 }else if(t<18){
  stall(729,442,274,t);perform(0,347,442,64,t,t>16?'sad':'idle');rect(500,429,70,5,C.wood);rect(506,434,4,9,C.wood);rect(562,434,4,9,C.wood);
  const action=t<12.5?'reach':t<14.5?'inspect':t<15?'place':t<16?'refuse':t<16.25?'turn':'idle';
  const a=t>=16.25?moveActor(2,580,646,442,64,t,16.25,17.6):perform(2,580,442,64,t,action,{flip:true});
  if(t>=12.5&&t<15)heldCloth(a,29);else{rect(522,419,29,9,'#d6c29a');stroke(522,422,551,422,'#b8a478',2)}
  text('先做动作，再给反应',480,137,22,C.muted);
 }else if(t<25){
  const active=t>=22;powered(584,442,244,t,.6,active);let a=perform(1,432,442,128,t,t<19?'place':t<20?'carry':t<21?'push':t<22?'nod':'work');
  if(t<20.8){const u=go(t,20,20.8);cog(lerp(a.right[0],511,u),lerp(a.right[1],393,u),23,0);a.hands()}else if(t<22)cog(511,393,23,0);
  if(active){stroke(511,393,a.right[0],a.right[1],C.wood,4);a.hands()}
  text('近景只负责让关键接触看清',480,137,22,C.muted);
 }else{
  shop(260,442,286,'目的地',C.teal);perform(1,431,442,64,t,'idle',{flip:true});
  for(let i=0;i<4;i++)moveActor(2,980+i*65,543+i*69,442,64,t,25+i*.5,27.7+i*.5,i===0?'nod':'idle',true);
  text('小人物 · 大行动空间 · 有目的地移动',480,137,22,C.muted);
 }
}
