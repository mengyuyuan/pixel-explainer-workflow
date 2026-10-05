/* Absolute-time pixel performance. Source art is generated; all object ownership
   and timing live here. A seek never relies on an earlier frame's state. */
const poseCache=new Map();
function poseBitmap(row,col){
 const key=row+':'+col;if(poseCache.has(key))return poseCache.get(key);
 const data=PERFORMERS[row],a=data.poses[col],ref=data.poses[0];
 const c=document.createElement('canvas');c.width=96;c.height=80;
 const g=c.getContext('2d');g.imageSmoothingEnabled=false;
 const s=64/ref.box[3],b=a.box,dx=Math.round(48+(b[0]-a.rootX)*s),dy=Math.round(72+(b[1]-a.baseline)*s);
 const dw=Math.round(b[2]*s),dh=Math.round(b[3]*s);
 g.drawImage(imgs[data.key],...b,dx,dy,dw,dh);
 const point=v=>[dx+(v[0]-b[0])*dw/b[2],dy+(v[1]-b[1])*dh/b[3]];
 const result={canvas:c,right:point(a.right),left:point(a.left),col};poseCache.set(key,result);return result;
}
function perform(row,x,y,h,t,action='idle',options={}){
 const flip=!!options.flip,scale=Math.max(1,Math.round(h/64));let col;
 if(action==='carryWalk')col=13;
 else if(action==='walk')col=5+Math.floor(Math.abs(options.distance??t*54)/(scale*7))%4;
 else if(action==='work')col=((t*(options.rate||1.45)+(options.phase||0))%1)<.5?11:12;
 else if(action==='speak')col=2+(Math.floor(t*7)%3===0?0:1);
 else if(action==='idle')col=((t+row*.71)%4.7)>.0&&((t+row*.71)%4.7)<.14?1:0;
 else col=PERFORMERS[row].poses.findIndex(v=>v.name===action);
 if(col<0)col=0;const a=poseBitmap(row,col),xx=Math.round(x),yy=Math.round(y);
 shadow(xx,yy+1,scale*34);p.save();p.translate(xx,yy);if(flip)p.scale(-1,1);
 if(action==='carryWalk'){
  const legs=poseBitmap(row,5+Math.floor(Math.abs(options.distance??t*54)/(scale*7))%4);
  p.drawImage(a.canvas,0,0,96,49,-48*scale,-72*scale,96*scale,49*scale);
  p.drawImage(legs.canvas,0,49,96,31,-48*scale,-23*scale,96*scale,31*scale);
 }else p.drawImage(a.canvas,-48*scale,-72*scale,96*scale,80*scale);p.restore();
 const world=v=>[xx+(v[0]-48)*scale*(flip?-1:1),yy+(v[1]-72)*scale];
 return {right:world(a.right),left:world(a.left),x:xx,y:yy,scale,col,
  hands(){p.save();p.translate(xx,yy);if(flip)p.scale(-1,1);for(const v of [a.left,a.right]){const sx=Math.round(v[0]-3),sy=Math.round(v[1]-2);p.drawImage(a.canvas,sx,sy,6,5,(sx-48)*scale,(sy-72)*scale,6*scale,5*scale)}p.restore()}};
}
function moveActor(row,x0,x1,y,h,t,start,end,after='idle',flip=false,carrying=false){
 const u=go(t,start,end),x=Math.round(lerp(x0,x1,u));
 return perform(row,x,y,h,t,u>0&&u<1?(carrying?'carryWalk':'walk'):after,{flip,distance:x-x0});
}
function heldCloth(a,width=60){
 width=Math.min(width,a.scale*28);
 const cx=(a.left[0]+a.right[0])/2,cy=(a.left[1]+a.right[1])/2;
 const height=Math.max(7,Math.round(width*.25)),top=cy-height+2;
 rect(cx-width/2-1,top-1,width+2,height+2,'#766748');rect(cx-width/2,top,width,height,'#d6c29a');
 for(let i=0;i<width;i+=6)rect(cx-width/2+i,top+1,2,height-2,'#b8a478');stroke(cx-width/2,top+height*.5,cx+width/2,top+height*.5,'#eee0ba',1);a.hands();
}
function heldPaper(a,priceText=''){
 const [x,y]=a.right,w=24*a.scale,h=18*a.scale,left=x-w*.6,top=y-h*.65;
 rect(left-1,top-1,w+2,h+2,'#8a795b');rect(left,top,w,h,C.ivory);
 if(priceText)text(priceText,left+w/2,top+h/2,12*a.scale,C.red);else for(let i=0;i<3;i++)rect(left+4*a.scale,top+(4+i*4)*a.scale,15*a.scale,a.scale,C.muted);a.hands();
}
function operatedLoom(row,x,y,w,t,progress=.7,working=true,options={}){
 const clockT=t*(options.rate||1),isPowered=!!options.powered;
 if(isPowered)powered(x,y,w,clockT,progress,working);else loom(x,y,w,clockT,progress,working);
 const h=options.height||64,px=x-w*.43-h*.17;
 const a=perform(row,px,y+3,h,clockT,working?'work':(options.rest||'carry'),{phase:options.phase||0,rate:options.cycle||1.45});
 if(working){const hand=a.right,hy=y-w*.21;stroke(x-w*.20,hy,hand[0],hand[1],'#493723',6);stroke(x-w*.20,hy,hand[0],hand[1],'#ba8f50',2);rect(hand[0]-4,hand[1]-4,8,8,'#705133');a.hands()}
 else if((options.rest||'carry')==='carry')heldCloth(a,w*.24);
 return a;
}
