"""stagedemo3: three different connections. Run after BlenderMCP exports v14 models."""
from pathlib import Path
import hashlib,json,math
ROOT=Path(__file__).resolve().parents[1]
ES=[]
STONE=[.40,.39,.32];DARK=[.055,.105,.115];GOLD=[.95,.48,.10]
def ent(n,p=(0,0,0),s=(1,1,1),r=(0,0,0),parent=None):
    e=dict(name=n,guid=hashlib.sha256(('stagedemo3v14/'+n).encode()).hexdigest()[:16],transform=dict(position=list(p),scale=list(s),rotation=list(r)))
    if parent:e['parentGuid']=parent['guid']
    ES.append(e);return e
def col(e,moving=False):
    e['boxCollider']=dict(halfExtents=[.5,.5,.5],offset=[0,0,0])
    e['rigidBody']=dict(motionType=1 if moving else 0,mass=1,friction=.7,restitution=0,useGravity=False)
    return e
def block(n,p,s,c=STONE,solid=True,glow=False,r=(0,0,0)):
    e=ent(n,p,s,r);e.update(primitive='box',color=c,material=dict(metallic=.03,roughness=.85))
    if solid:col(e)
    if glow:e.update(shader='ReconnectInk.hlsl',shaderParams=c+[1])
    return e
def hit(n,p,s,moving=False,r=(0,0,0)):return col(ent(n,p,s,r),moving)
def model(n,asset,p=(0,0,0),s=(1,1,1),r=(0,0,0)):
    e=ent(n,p,s,r);e['meshRenderer']=dict(modelPath='models/stagedemo3_v14/'+asset+'.gltf');return e
def floor(n,z0,z1,y=0,w=21,x=0):
    block(n,(x,y-.25,(z0+z1)/2),(w,.5,z1-z0))
    for z in range(math.ceil(z0),math.ceil(z1),3):block(n+'joint'+str(z),(x,y+.003,z),(w,.006,.018),DARK,False,True)
def light(n,p):
    e=ent(n,p);e['pointLight']=dict(color=[1,.89,.72],intensity=24,range=24,castShadows=False)
def line(n,a,b,width=.035,c=GOLD):
    d=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(x*x for x in d))
    return block(n,[(a[i]+b[i])/2 for i in range(3)],(width,width,length),c,False,True,(-math.degrees(math.atan2(d[1],math.hypot(d[0],d[2]))),math.degrees(math.atan2(d[0],d[2])),0))
def build():
    ES.clear()
    e=ent('V14_Sun');e['directionalLight']=dict(direction=[-.4,-.8,.15],color=[1,.95,.84],intensity=.9,ambient=.28)
    floor('Entrance',-9,28);floor('UpperGallery',44,64,3.2);floor('FinalBalcony',80,95,6.4)
    floor('PitBottom',-9,95,-12,23)
    for x in [-10.8,10.8]:block('SideWall'+str(x),(x,3,43),(.6,31,106),DARK)
    block('BackWall',(0,6,-9),(22,14,.5),DARK)
    block('EndWall',(0,10.5,95),(22,11,.5),DARK)
    for z in [-5,16,24,48,58,85,93]:
        y=0 if z<28 else (3.2 if z<80 else 6.4)
        model('Vault'+str(z),'vault_rib',(0,y,z))
        light('Pool'+str(z),(0,y+8,z))
    for z in range(-6,94,6):
        y=0 if z<28 else (3.2 if z<80 else 6.4)
        for x in [-10.3,10.3]:block('WallLamp'+str(x)+'_'+str(z),(x,y+4,z),(.06,1.6,.22),[.85,.64,.34],False,True)
    # Staggered, complementary arches share an exact projection from the sight ring.
    for side,k in [('Left',.75),('Right',1.25)]:
        model('Seam'+side,'seam_'+side.lower(),(0,1.7*(1-k),10*k),(k,k,k))
    model('Sight01','sight_ring',(0,.01,0))
    model('Console01','connection_console',(-2,0,0))
    for side in [-1,1]:hit('SeamWall'+str(side),(side*6,4,10),(8.7,8,4))
    hit('SeamHeader',(0,6,10),(3.3,3.5,4))
    col(block('SeamSeal',(0,2.95,14),(4.6,5.9,.14),DARK,False),True)
    for x in [-.9,-.45,0,.45,.9]:block('SealThread'+str(x),(x*1.4,2.95,13.9),(.018,5.8,.022),GOLD,False,True)
    for side in [-1,1]:
        block('SeamAlcove'+str(side),(side*9.1,4,5.5),(3.3,8,.5),DARK)
        block('SeamReveal'+str(side),(side*7.35,4,10),(.2,8,9),DARK)
    # Foot-level breadcrumbs lead to the first ring and onward after connecting.
    for z in [-4,-3,-2]:line('Lead01'+str(z),(0,.025,z),(0,.025,z+.4),.04)
    # Painting room: the frame encloses a split path at three depths.
    model('PaintingFrame','painting_frame',(0,0,36))
    block('PaintingBackdrop',(0,3.6,41.5),(20,9,.18),[.12,.23,.22],False)
    for i in range(9):
        x=-9+i*2.25
        line('PictureHatch'+str(i),(x,-.1,41.37),(x+2,7,41.37),.018,[.22,.32,.29])
    for j,k in enumerate([.72,1.24,.86]):
        target=(-8+16*j/3,3.2*j/3,36);eye=(0,4.5,18)
        initial=tuple(eye[i]+(target[i]-eye[i])*k for i in range(3))
        model('PaintingPath'+str(j),'painted_path_'+str(j),initial,(k,k,k))
    # Thin collision ramps, enabled at the end of the projection animation.
    angle=math.degrees(math.atan(.2))
    for j in range(3):
        x=-8+16*(j+.5)/3;y=3.2*(j+.5)/3
        hit('PaintingCollider'+str(j),(x,y-.14-35,36),(math.hypot(16/3,3.2/3)+.04,.28,1.65),True,(0,0,angle))
    model('PaperWalker','paper_walker',(-5.76,1.26,30.96),(.72,.72,.72))
    model('Sight02','sight_ring',(0,.01,24))
    model('Console02','connection_console',(-1.9,0,24))
    floor('PictureExitWalk',35,45,3.2,2.3,8)
    for z in [38,41,44]:
        for x in [6.85,9.15]:block('PictureRail'+str(x)+str(z),(x,3.8,z),(.055,1.2,.055),DARK)
    for x in [6.85,9.15]:line('PictureHandrail'+str(x),(x,4.4,38),(x,4.4,45),.04)
    # Sculpted stairs rotate in a vertical plane: the roof literally becomes the floor.
    model('CeilingStair','inverted_stair',(0,7.2,72),r=(0,0,180))
    model('Sight03','sight_ring',(0,3.21,60))
    model('Console03','connection_console',(-2,3.2,60))
    for i in range(16):
        top=3.2+.2*(i+1)
        hit('StairCollider'+str(i),(0,top-.1-40,64+i+.5),(3.8,.2,1.035),True)
    for x in [-2.6,2.6]:
        line('HingeSupport'+str(x),(x,3.2,63.5),(x,12.4,63.5),.13,[.24,.31,.29])
        line('HingeCable'+str(x),(x,12.4,63.5),(x,12.4,80),.04,[.24,.31,.29])
    for z,y in [(28,0),(64,3.2),(80,6.4)]:
        for side in [-1,1]:
            block('EdgeGuard'+str(z)+str(side),(side*6.4,y+.4,z),(8,.8,.16),DARK)
            line('GuardTop'+str(z)+str(side),(side*2.4,y+.83,z),(side*10.4,y+.83,z),.04,[.55,.59,.47])
    model('RewardKnot','connected_knot',(0,6.4,91))
    model('FinalRing','sight_ring',(0,6.41,87))
    for x in [-1.8,1.8]:line('ExitGuide'+str(x),(x,6.425,81),(x,6.425,88),.045)
    player=ent('V14_Player',(-3,.91,-4))
    player['characterController']=dict(radius=.35,halfHeight=.55,offset=[0,0,0],stepHeight=.26,jumpSpeed=4.5,gravityScale=1,mass=70,maxSlopeDeg=50)
    cam=ent('V14_Camera',(-3,1.71,-4));cam['camera']=dict(fovDegrees=68,nearClip=.04,farClip=200,projection=0,isActive=True)
    e=ent('V14_Logic');e['luaScript']=dict(enabled=True,scriptPath='components/Stagedemo3Gallery.lua')
    canvas=ent('V14_HUD');canvas['uiCanvas']=dict(refWidth=1600,refHeight=900,scaleMode=0,sortOrder=0,visible=True)
    for n,text,t,b,size,c in [
        ('Chapter','01  穴を縫う',48,88,27,[.97,.91,.78,1]),
        ('Hint','床の大きな輪に立ち、二つの半円を重ねる',772,822,26,[1,.87,.59,1]),
        ('Keys','WASD  歩く   マウス / 矢印  見る   E  つなぐ   R  足場へ戻る   ESC  マウス解放',830,868,22,[.82,.85,.80,1])]:
        e=ent('V14_'+n,parent=canvas);e['uiRect']=dict(anchorMin=[0,0],anchorMax=[1,0],offsetMin=[48,t],offsetMax=[-48,b],visible=True)
        e['uiText']=dict(text=text,fontSize=size,color=c,alignH=0,alignV=1,wrap=False,outlineWidth=1.3,outlineColor=[.01,.015,.015,1])
    return dict(version=1,entities=ES,shadows=True,skybox=dict(drawSkybox=False,envMapPath='',iblIntensity=0,skyboxIntensity=0),ssao=dict(enabled=True,radius=.65,intensity=.65,power=1.3,bias=.025,blur=True,sampleCount=16),postProcess=dict(enabled=True,tonemapper=1,exposureOn=True,exposure=1.12,bloomOn=True,bloom=.12,bloomThreshold=1.4,fxaaOn=True,vignetteOn=True,vignette=.12,grainOn=False,caOn=False))
def main():
    data=build()
    (ROOT/'assets/scenes/stagedemo3.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    code=(ROOT/'source/stagedemo3_v14_runtime.lua').read_text(encoding='utf-8')
    (ROOT/'assets/components/Stagedemo3Gallery.lua').write_text(code,encoding='utf-8')
    print(f'stagedemo3 v14: {len(ES)} entities, 12 Blender modules, 3 distinct connections')
if __name__=='__main__':main()
