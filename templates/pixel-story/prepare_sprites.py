from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import label,find_objects
P=Path(__file__).parent
names=['idle','blink','talkClosed','talkOpen','think','walkContactA','walkPassA','walkContactB','walkPassB','turn','reach','push','pull','carry','place','inspect','refuse','surprise','sad','nod']
# Hand anchors are normalized to the visible sprite bounds, reviewed against generated art.
grips={10:((.95,.50),(.18,.69)),11:((.91,.52),(.80,.52)),12:((.82,.60),(.52,.61)),13:((.83,.65),(.48,.65)),14:((.91,.80),(.73,.80)),15:((.79,.51),(.53,.65)),16:((.94,.41),(.24,.71)),2:((.92,.49),(.15,.72)),3:((.92,.49),(.15,.72)),17:((.90,.42),(.15,.46))}
result=[]
for spec in json.loads((P/'sprites.json').read_text(encoding='utf-8')):
    key=spec['key']
    f=P/spec['file'];im=Image.open(f).convert('RGBA');w,h=im.size;poses=[]
    for i,name in enumerate(names):
        row,col=divmod(i,5);x,y=round(col*w/5),round(row*h/4);xx,yy=round((col+1)*w/5),round((row+1)*h/4)
        mask=np.asarray(im)[y:yy,x:xx,3]>100;components,count=label(mask);sizes=np.bincount(components.ravel());sizes[0]=0
        assert count>0,(key,name)
        sy,sx=find_objects(components)[int(sizes.argmax())-1]
        b=[x+max(0,sx.start-1),y+max(0,sy.start-1),min(xx-x,sx.stop+1)-max(0,sx.start-1),min(yy-y,sy.stop+1)-max(0,sy.start-1)]
        footmask=np.asarray(im)[b[1]+round(b[3]*.92):b[1]+b[3],b[0]:b[0]+b[2],3]>100
        fx=np.nonzero(footmask)[1];anchor=b[0]+float((fx.min()+fx.max())/2)
        pair=grips.get(i,((.77,.72),(.20,.72)))
        poses.append({'name':name,'box':b,'rootX':anchor,'baseline':b[1]+b[3],'right':[b[0]+pair[0][0]*b[2],b[1]+pair[0][1]*b[3]],'left':[b[0]+pair[1][0]*b[2],b[1]+pair[1][1]*b[3]]})
    result.append({'key':key,'file':spec['file'],'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'size':[w,h],'alphaRange':im.getchannel('A').getextrema(),'poses':poses})
(P/'assets/performers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'performer-data.js').write_text('const PERFORMERS='+json.dumps(result,ensure_ascii=False)+';',encoding='utf-8')
print(json.dumps([{k:v for k,v in a.items() if k!='poses'} for a in result],ensure_ascii=False))
