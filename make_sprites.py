import sys,pathlib
local_vendor=pathlib.Path(__file__).parent/'vendor'
sys.path.insert(0,str(local_vendor))
import pixel_sprite as kit
p=pathlib.Path(__file__).parent/'assets'
p.mkdir(exist_ok=True)
kit.PAL.update({'U':'e89b49','u':'b86636','H':'263446','h':'41546a','P':'314659','p':'223146','K':'111f2a'})
poses={}
for name in ['idle','blink','talk','cheer','walk1','walk2','point']:
 g=kit.pose(name if name in ['blink','talk','cheer'] else 'idle')
 if name.startswith('walk'):
  for y in range(22,30):
   for x in range(3,15):g.put(x,y,'.')
  k=1 if name=='walk1' else -1
  g.rect(5-k,22,8-k,26,'P');g.rect(9+k,22,12+k,27,'p');g.rect(4-k,27,8-k,28,'F');g.rect(9+k,28,13+k,29,'f')
 if name=='point':
  g.rect(14,13,18,15,'S');g.put(18,12,'S')
 g.outline();poses[name]=g;kit.save(g,str(p/f'hero-{name}.png'))
kit.sheet(list(poses.values()),str(p/'sprite-sheet.png'))
print('7 poses generated with upstream Grid, outline and PNG writer')
