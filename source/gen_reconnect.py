"""Junction RECONNECT: deterministic, independent successor to stagedemo3.

Generate: python source/gen_reconnect.py
The previous generator, scene and Lua controller are deliberately independent.
Every unsolved fragment is a homothety about the intended observer; connecting
interpolates that homothety to identity, preserving the observer's projection.
"""
from pathlib import Path
import json, math, hashlib

ROOT = Path(__file__).resolve().parents[1]
ENTITIES, PUZZLES = [], []
STONE = [.46, .44, .39]
DARK = [.055, .073, .08]
FLOOR = [.31, .34, .33]
AMBER = [.90, .42, .095]

def entity(name, p=(0,0,0), s=(1,1,1), r=(0,0,0), parent=None):
    e = dict(name=name, guid=hashlib.sha256(('reconnect/'+name).encode()).hexdigest()[:16],
             transform=dict(position=list(p), scale=list(s), rotation=list(r)))
    if parent: e['parentGuid'] = parent['guid']
    ENTITIES.append(e)
    return e

def box(name,p,s,c=STONE,r=(0,0,0),solid=True,parent=None,light=False):
    e=entity(name,p,s,r,parent)
    e.update(primitive='box',color=c,material=dict(metallic=.05,roughness=.86))
    if light: e.update(shader='ReconnectInk.hlsl',shaderParams=list(c)+[1])
    if solid: collider(e)
    return e

def collider(e, moving=False):
    e['boxCollider']=dict(halfExtents=[.5,.5,.5],offset=[0,0,0])
    e['rigidBody']=dict(motionType=1 if moving else 0,mass=1,friction=.7,
                        restitution=0,useGravity=False)

def floor(name,z0,z1,y=0,w=20,x=0):
    return box(name,(x,y-.3,(z0+z1)/2),(w,.6,z1-z0),FLOOR)

def ink(name,p,s,c=AMBER,r=(0,0,0),parent=None):
    return box(name,p,s,c,r,False,parent,True)

def lamp(name,p,intensity=12,color=(1,.86,.67),rng=20):
    e=entity(name,p)
    e['pointLight']=dict(color=list(color),intensity=intensity,range=rng,castShadows=False)

def line(name,a,b,width=.055,c=AMBER,parent=None):
    d=[b[i]-a[i] for i in range(3)]
    length=math.sqrt(sum(v*v for v in d))
    yaw=math.degrees(math.atan2(d[0],d[2]))
    pitch=-math.degrees(math.atan2(d[1],math.hypot(d[0],d[2])))
    return ink(name,[(a[i]+b[i])/2 for i in range(3)],(width,width,length),c,(pitch,yaw,0),parent)

def floor_mark(name,x,z,exact=False,y=0):
    # A broad walking rail; only tutorial has a full observer cross.
    line(name+'Rail',(x-2,y+.018,z),(x+2,y+.018,z),.042)
    for side in [-1,1]: line(name+str(side),(x+side*2,y+.018,z-.22),(x+side*2,y+.018,z+.22),.042)
    if exact:
        line(name+'Eye',(x,y+.024,z-.28),(x,y+.024,z+.28),.055)
        for side in [-1,1]: ink(name+'Foot'+str(side),(x+side*.23,y+.02,z-.4),(.11,.025,.28))

def arch(name,z,y=0):
    box(name+'Left',(-3.1,y+3,z),(1,6,.75),STONE)
    box(name+'Right',(3.1,y+3,z),(1,6,.75),STONE)
    box(name+'Top',(0,y+5.7,z),(5.2,.6,.75),STONE)
    for x in [-2.59,2.59]: ink(name+'Light'+str(x),(x,y+2.8,z-.4),(.04,5.6,.04))
    box(name+'InfillL',(-7,y+5,z),(6,10,.5),DARK)
    box(name+'InfillR',(7,y+5,z),(6,10,.5),DARK)

def digit(name,n,x,y,z,scale=1):
    segs={'a':(0,1,.65,.08),'b':(.35,.5,.08,.9),'c':(.35,-.5,.08,.9),
          'd':(0,-1,.65,.08),'e':(-.35,-.5,.08,.9),'f':(-.35,.5,.08,.9),'g':(0,0,.65,.08)}
    for s in {0:'abcdef',1:'bc',2:'abged',3:'abcdg'}[n]:
        dx,dy,w,h=segs[s]
        ink(name+s,(x+dx*scale,y+dy*scale,z),(w*scale,h*scale,.025),[.65,.63,.55])

def puzzle(pid,title,eye,path,ratios,zone,checkpoint,helptext):
    p=dict(id=pid,title=title,eye=list(eye),zone=zone,checkpoint=list(checkpoint),
           help=helptext,parts=[],joins=[],tol=1.8)
    for i,(a,b,k) in enumerate(zip(path,path[1:],ratios)):
        delta=[b[j]-a[j] for j in range(3)]
        length=math.sqrt(sum(q*q for q in delta))
        yaw=math.degrees(math.atan2(delta[0],delta[2]))
        pitch=-math.degrees(math.atan2(delta[1],math.hypot(delta[0],delta[2])))
        # Root includes the slab, side ink and visible split-joint beads.
        root=entity(f'P{pid}_Fragment{i+1}',eye,(k,k,k))
        target=[sum(v)/2 for v in zip(a,b)]
        initial=[eye[j]+(target[j]-eye[j])*k for j in range(3)]
        root['transform']['position']=initial
        r=(pitch,yaw,0)
        slab=box(f'P{pid}_Slab{i+1}',(0,-.20,0),(2.6,.4,length+.035),[.43,.39,.31],r,False,root)
        # All children are expressed relative to an unrotated root.
        angle=math.radians(yaw)
        right=(math.cos(angle),0,-math.sin(angle))
        for side in [-1,1]:
            aa=[a[j]-target[j]+right[j]*1.20*side for j in range(3)]
            bb=[b[j]-target[j]+right[j]*1.20*side for j in range(3)]
            aa[1]+=.027;bb[1]+=.027
            line(f'P{pid}_Edge{i+1}_{side}',aa,bb,.07,parent=root)
        line(f'P{pid}_Spine{i+1}',[a[j]-target[j]+(.032 if j==1 else 0) for j in range(3)],
             [b[j]-target[j]+(.032 if j==1 else 0) for j in range(3)],.032,parent=root)
        c=entity(f'P{pid}_Collider{i+1}',(target[0],target[1]-30,target[2]),(2.6,.4,length+.06),r)
        collider(c,True)
        p['parts'].append(dict(root=root['name'],collider=c['name'],target=target,k=k,
                               solid=[target[0],target[1]-.20,target[2]],length=length))
        if i:
            # Two lateral points prevent a center-only false alignment.
            prev=ratios[i-1]
            for side in [-1,1]:
                q=[a[j]+right[j]*.95*side+(.04 if j==1 else 0) for j in range(3)]
                u=[eye[j]+(q[j]-eye[j])*prev for j in range(3)]
                v=[eye[j]+(q[j]-eye[j])*k for j in range(3)]
                p['joins'].append([u,v])
                for label,pos in [('A',u),('B',v)]:
                    bead=entity(f'P{pid}_Joint{i}_{side}{label}',pos,(.13,.13,.13))
                    bead.update(primitive='sphere',color=AMBER,shader='ReconnectInk.hlsl',shaderParams=AMBER+[1])
                    # Render joint beads are updated along the same ray as the fragments.
                    p.setdefault('beads',[]).append(dict(name=bead['name'],target=q,k=prev if label=='A' else k))
    PUZZLES.append(p)

def lua(v):
    if isinstance(v,dict): return '{'+','.join('['+json.dumps(k)+']='+lua(x) for k,x in v.items())+'}'
    if isinstance(v,(list,tuple)): return '{'+','.join(map(lua,v))+'}'
    if isinstance(v,str): return json.dumps(v,ensure_ascii=False)
    if isinstance(v,bool): return 'true' if v else 'false'
    return str(v)

def build():
    sun=entity('GallerySun');sun['directionalLight']=dict(direction=[-.4,-.8,.25],color=[1,.94,.84],intensity=.75,ambient=.19)
    floor('Arrival',-10,4);floor('Landing01',14,36);floor('Landing02',50,69)
    floor('Island',74,78,w=5)
    floor('ExitBalcony',87,95,y=3.2)
    floor('DeepPit',-11,97,y=-11,w=23)
    for x in [-10.3,10.3]:
        box('GalleryWall'+str(x),(x,3,42),(0.6,28,108),STONE if x<0 else DARK)
    box('ArrivalWall',(0,4,-10),(21,10,.6),DARK)
    box('ExitWall',(0,8,95),(21,12,.6),STONE)
    box('GalleryRoof',(0,10.45,42),(21,.45,106),DARK)
    for z in range(-6,95,8):
        for x in [-9.5,9.5]:
            box(f'Pier_{x}_{z}',(x,4,z),(.5,8,.7),[.25,.27,.26])
            ink(f'PierLamp_{x}_{z}',(x+( .27 if x<0 else -.27),3.5,z),(.035,1.8,.12),[.65,.62,.51])
        box(f'RoofRib{z}',(0,10,z),(20,.45,.5),DARK)
    for z in [-4,17,28,53,63,89]:
        lamp('GalleryLight'+str(z),(0,7.5,z),20,rng=24)
    for z0,z1,y in [(-9,4,0),(14,36,0),(50,69,0),(87,95,3.2)]:
        for z in range(z0,z1,2):
            ink(f'FloorJoint_{z}',(0,y+.006,z),(19.8,.006,.015),[.13,.15,.15])
        for x in [-7,-3,3,7]:
            ink(f'FloorJointX_{x}_{z0}',(x,y+.007,(z0+z1)/2),(.015,.006,z1-z0),[.13,.15,.15])
    # Visible guardrails stop detours and identify the edges of each real platform.
    for z in [4,14,36,50,69,87]:
        y=3.2 if z==87 else 0
        for side in [-1,1]:
            box(f'Guard_{z}_{side}',(side*6.05,y+.30,z),(7.9,.60,.15),DARK)
            ink(f'GuardInk_{z}_{side}',(side*6.05,y+.615,z),(7.9,.035,.16),[.45,.47,.42])
    arch('Passage01',23);arch('Passage02',58);arch('ExitFrame',92,3.2)
    for n,z in [(1,22.7),(2,57.7),(3,94.6)]:
        digit(f'Zero{n}',0,-7,3.5,z,1.25);digit(f'Number{n}',n,-5.7,3.5,z,1.25)
    # Solid physical exit gate visibly retracts when the complete route is stitched.
    gate=box('ExitGate',(0,5.7,92),(5.1,5,.25),DARK);gate['rigidBody']['motionType']=1
    for x in [-1.2,0,1.2]: ink('ExitGateMark'+str(x),(x,5.7,91.84),(.08,3,.04),AMBER)
    floor_mark('Observe01',0,0,True)
    floor_mark('Observe02',-4.5,30.5)
    floor_mark('Observe03',4,64)
    floor_mark('Observe04',0,76,True)
    # A single continuous solution evolves: straight / folded corner / interrupted ascent.
    puzzle(1,'01  切れた線',(0,1.7,0),[(0,0,z) for z in [4,6.5,9,11.5,14]],
           [.58,1.32,.72,1.12],[-9,19],[-2,.91,-5],
           '床の印で左右に歩き、金色の線を一本に重ねる')
    puzzle(2,'02  角の向こう',(-4.5,1.7,30.5),[(0,0,36),(0,0,41),(5.6,0,41),(5.6,0,46),(0,0,46),(0,0,50)],
           [.58,1.23,.73,1.09,.84],[24,56],[0,.91,27],
           '横へ歩く。離れた角をつなぐと、曲がった道になる')
    puzzle(3,'03  空中の踊り場',(4,1.7,64),[(0,0,z) for z in [69,70.6,72.3,74]],
           [.55,1.2,.76],[59,74],[0,.91,62],
           'まず手前の線をつないで、中央の島へ渡る')
    puzzle(4,'03  空中の踊り場',(0,1.7,76),[(0,.8*i,78+2.25*i) for i in range(5)],
           [1.24,.68,1.38,.85],[74,90],[0,.91,76],
           '島からもう一度つなぐ。宙に浮いた線が上り道になる')
    body=entity('ReconnectPlayer',(-2,.91,-5))
    body['characterController']=dict(radius=.35,halfHeight=.55,offset=[0,0,0],stepHeight=.25,
        jumpSpeed=4.5,gravityScale=1,mass=70,maxSlopeDeg=50)
    cam=entity('ReconnectCamera',(-2,1.71,-5))
    cam['camera']=dict(fovDegrees=68,nearClip=.04,farClip=220,projection=0,isActive=True)
    control=entity('ReconnectLogic')
    control['luaScript']=dict(enabled=True,scriptPath='components/Reconnect.lua')
    canvas=entity('ReconnectHUD');canvas['uiCanvas']=dict(refWidth=1600,refHeight=900,scaleMode=0,sortOrder=0,visible=True)
    for name,text,top,bottom,size,color in [
        ('Chapter','JUNCTION / RECONNECT',42,82,25,[.95,.91,.82,1]),
        ('Hint','床の印で左右に歩き、金色の線を一本に重ねる',776,824,25,[1,.91,.72,1]),
        ('Keys','WASD  歩く    マウス  見る    E  つなぐ    R  足場へ戻る    ESC  マウス解放',836,872,22,[.80,.82,.80,1])]:
        e=entity('HUD_'+name,parent=canvas)
        e['uiRect']=dict(anchorMin=[0,0],anchorMax=[1,0],offsetMin=[48,top],offsetMax=[-48,bottom],visible=True)
        e['uiText']=dict(text=text,fontSize=size,color=color,alignH=0,alignV=1,wrap=False,outlineWidth=1.2,
                         outlineColor=[.015,.02,.02,1])
    scene=dict(version=1,entities=ENTITIES,shadows=True,
        skybox=dict(drawSkybox=False,envMapPath='',iblIntensity=0,skyboxIntensity=0),
        ssao=dict(enabled=True,radius=.65,intensity=.7,power=1.3,bias=.025,blur=True,sampleCount=16),
        postProcess=dict(enabled=True,tonemapper=1,exposureOn=True,exposure=1.05,
                         bloomOn=True,bloom=.17,bloomThreshold=1.3,fxaaOn=True,
                         vignetteOn=True,vignette=.13,grainOn=False,caOn=False))
    return scene

if __name__=='__main__':
    scene=build()
    out=ROOT/'assets/scenes/reconnect.json'
    out.write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
    runtime=(ROOT/'source/reconnect_runtime.lua').read_text(encoding='utf-8')
    (ROOT/'assets/components/Reconnect.lua').write_text('-- Generated by source/gen_reconnect.py\nlocal PUZZLES = '+lua(PUZZLES)+'\n'+runtime,encoding='utf-8')
    (ROOT/'source/reconnect_geometry.json').write_text(json.dumps(PUZZLES,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{out}: {len(ENTITIES)} entities, {len(PUZZLES)} connections')
