-- STAGEDEMO3 / THE CONNECTED GALLERY. Authored Blender meshes + explicit connections.
local function find(n) local e=scene:findEntity(n);assert(e and e:isValid(),'Gallery missing '..n);return e end
local function v(x,y,z) return Vec3.new(x,y,z) end
local function smooth(t) t=math.max(0,math.min(1,t));return t*t*(3-2*t) end
local function text(self,k,s) if self.text[k]~=s then scene:setUiText(self.ui[k],s);self.text[k]=s end end
local function sound() audio:playSFXId('audio/ui/connect.wav',false,.55) end
local function setpos(self,p) physics:setPosition(self.body,v(p[1],p[2],p[3])) end
local function firstcamera(self)
    local p=self.body.transform.position
    self.cam.transform.position=v(p.x,p.y+.8,p.z);self.cam.transform.rotation=v(-self.pitch,self.yaw,0);self.cam:setFov(68)
end
local function flatparts(t)
    for j,k0 in ipairs({.72,1.24,.86}) do
        local k=k0+(1-k0)*t;local x=-8+16*(j-1)/3;local y=3.2*(j-1)/3
        local e=find('PaintingPath'..(j-1));e.transform.position=v(x*k,4.5+(y-4.5)*k,18+18*k);e.transform.scale=v(k,k,k)
    end
    local k=.72+.28*t;local w=find('PaperWalker')
    w.transform.position=v(-8*k,4.5*(1-k),18+18*k);w.transform.scale=v(k,k,k)
end
local function paintingcolliders(on)
    for j=0,2 do
        local e=find('PaintingCollider'..j)
        -- Re-register at the destination, instead of sweeping a kinematic ramp
        -- up through the walker and injecting a large platform velocity.
        if on then physics:removeRigidBody(e) end
        e.transform.position=v(-8+16*(j+.5)/3,3.2*(j+.5)/3-.14-(on and 0 or 35),36)
        if on then physics:addRigidBody(e,0,1) end
    end
end
local function staircolliders(on)
    for j=0,15 do find('StairCollider'..j).transform.position=v(0,3.2+.2*(j+1)-.1-(on and 0 or 40),64+j+.5) end
end
local function pose_seam(t)
    for j,k0 in ipairs({.75,1.25}) do
        local k=k0+(1-k0)*t;local e=find(j==1 and 'SeamLeft' or 'SeamRight')
        e.transform.position=v(0,1.7*(1-k),10*k);e.transform.scale=v(k,k,k)
    end
    find('SeamSeal').transform.position=v(0,2.95-9*t,14)
    for _,x in ipairs({'-0.9','-0.45','0','0.45','0.9'}) do find('SealThread'..x).transform.position=v(tonumber(x)*1.4,2.95-9*t,13.9) end
end
local function reset(self)
    log('GALLERY checkpoint return: '..self.mode)
    self.mode='walk';self.anim=0;self.yaw=0;self.pitch=0;setpos(self,self.checkpoint)
    if self.paint then find('PaperWalker').transform.position=v(0,-50,0)
    elseif self.flattened then flatparts(1) else flatparts(0) end
end
function OnStart(self)
    self.body=find('V14_Player');self.cam=find('V14_Camera');self.walker=find('PaperWalker')
    self.ui={Chapter=find('V14_Chapter'),Hint=find('V14_Hint'),Keys=find('V14_Keys')};self.text={}
    self.yaw=0;self.pitch=0;self.elapsed=0;self.mode='walk';self.anim=0
    self.seam=false;self.paint=false;self.stair=false;self.flattened=false;self.complete=false
    self.checkpoint={-3,.91,-4};self.check=0;self.step=0;self.ready=false
    pose_seam(0);flatparts(0);paintingcolliders(false);staircolliders(false)
    find('CeilingStair').transform.rotation=v(0,0,180)
    for _,n in ipairs({'seam','paint','stair','complete','ready','mode'}) do saveNum('gallery_'..n,0) end
    input:setMouseCapture(true);log('GALLERY v14: negative space / painting walk / ceiling inversion')
end
function OnUpdate(self,dt)
    dt=math.min(dt,.08);self.elapsed=self.elapsed+dt
    if self.elapsed<.6 then setpos(self,self.checkpoint) end
    if keyPressed('ESC') then input:setMouseCapture(not input:isMouseCaptured()) end
    if self.mode=='walk' and not self.complete then
        if input:isMouseCaptured() and loadNum('gallery_testMode',0)<.5 then
            self.yaw=self.yaw+input:getMouseDeltaX()*.085;self.pitch=self.pitch-input:getMouseDeltaY()*.085
        end
        if keyDown('LEFT') then self.yaw=self.yaw-80*dt end
        if keyDown('RIGHT') then self.yaw=self.yaw+80*dt end
        if keyDown('UP') then self.pitch=self.pitch+65*dt end
        if keyDown('DOWN') then self.pitch=self.pitch-65*dt end
        -- Opt-in camera fixture for MCP traversal tests. Does not affect progression.
        if loadNum('gallery_testMode',0)>.5 then self.yaw=loadNum('gallery_testYaw',0);self.pitch=loadNum('gallery_testPitch',0) end
    end
    self.yaw=self.yaw%360;self.pitch=math.max(-75,math.min(75,self.pitch))
    local p=self.body.transform.position
    if p.y< -5 and not self.complete then reset(self);p=self.body.transform.position end
    if keyPressed('R') and not self.complete and (self.mode=='walk' or self.mode=='painting') then reset(self);p=self.body.transform.position end
    if self.mode=='walk' and not self.complete then
        local yaw=math.rad(self.yaw);local x,z=0,0
        if keyDown('W') then x=x+math.sin(yaw);z=z+math.cos(yaw) end
        if keyDown('S') then x=x-math.sin(yaw);z=z-math.cos(yaw) end
        if keyDown('D') then x=x+math.cos(yaw);z=z-math.sin(yaw) end
        if keyDown('A') then x=x-math.cos(yaw);z=z+math.sin(yaw) end
        local len=math.sqrt(x*x+z*z)
        if len>0 then physics:move(self.body,x/len*3.8,z/len*3.8) else physics:move(self.body,0,0) end
        firstcamera(self)
    elseif self.mode~='painting' then physics:move(self.body,0,0) end
    -- Completed connections persist after falls; checkpoints advance only on real landings.
    if self.seam and p.z>16 and p.z<28 and self.check<1 then self.check=1;self.checkpoint={0,.91,23} end
    if self.paint and p.z>44 and self.check<2 then self.check=2;self.checkpoint={8,4.11,46} end
    if self.stair and p.z>81 and self.check<3 then self.check=3;self.checkpoint={0,7.31,83} end
    self.ready=false
    local facing=math.abs(((self.yaw+180)%360)-180)<22 and math.abs(self.pitch)<30
    local keys='WASD  歩く   マウス / 矢印  見る   E  つなぐ   R  足場へ戻る   ESC  マウス解放'
    if not self.seam then
        text(self,'Chapter','01  穴を縫う')
        self.ready=self.mode=='walk' and math.sqrt(p.x*p.x+p.z*p.z)<.7 and facing
        text(self,'Hint',self.ready and '半円がつながった。 E  穴を縫って、戸口にする' or '床の大きな輪に立ち、二つの半円を重ねる')
        if keyPressed('E') and self.ready then self.mode='seam';self.anim=0;sound() end
    elseif not self.paint then
        text(self,'Chapter','02  絵の中を歩く')
        self.ready=self.mode=='walk' and math.sqrt(p.x*p.x+(p.z-24)^2)<1.2 and facing
        text(self,'Hint',p.z<19 and 'つないだ穴をくぐる。その先には、歩ける絵がある' or (self.ready and 'E  自分を絵につなぐ。額縁の中に入る' or '次の床の輪へ。絵の中の人影と、自分をつなぐ'))
        if keyPressed('E') and self.ready then
            self.mode='enter';self.anim=0;self.from={self.cam.transform.position.x,self.cam.transform.position.y,self.cam.transform.position.z};sound()
        end
    elseif not self.stair then
        text(self,'Chapter','03  天井を床につなぐ')
        self.ready=self.mode=='walk' and math.sqrt(p.x*p.x+(p.z-60)^2)<1.3 and facing
        text(self,'Hint',p.z<46 and '絵から立体へ。右の通路を進む' or (self.ready and 'E  天井と床をつなぎ、逆さの階段を返す' or '天井に階段がある。正面の床の輪から、床につなぐ'))
        if keyPressed('E') and self.ready then self.mode='stair';self.anim=0;self.yaw=0;self.pitch=20;sound() end
    else
        text(self,'Chapter','03  天井を床につなぐ')
        text(self,'Hint','天井だった階段を上り、結び目の彫刻へ')
    end
    if self.mode=='seam' then
        self.anim=self.anim+dt/1.8;pose_seam(smooth(self.anim));text(self,'Hint','奥行きの違う二つの穴が、一つの戸口になる')
        if self.anim>=1 then self.seam=true;self.mode='walk';pose_seam(1);log('GALLERY seam connected') end
    elseif self.mode=='enter' then
        self.anim=self.anim+dt/2.2;local t=smooth(self.anim)
        self.cam.transform.position=v(self.from[1]*(1-t),self.from[2]+(4.5-self.from[2])*t,self.from[3]+(18-self.from[3])*t)
        self.cam.transform.rotation=v(0,0,0);self.cam:setFov(68-13*t);flatparts(t)
        text(self,'Hint','奥行きを絵につなぐ。見えている道が、歩ける道になる')
        if self.anim>=1 then
            flatparts(1);paintingcolliders(true);self.flattened=true;self.mode='painting';self.paintX=-7.8;setpos(self,{-7.8,.97,36});log('GALLERY entered painting')
        end
    elseif self.mode=='painting' then
        self.cam.transform.position=v(0,4.5,18);self.cam.transform.rotation=v(0,0,0);self.cam:setFov(55)
        -- In the picture, motion has one dimension. Sample the actual collision
        -- surface for feet placement; this also prevents gravity-driven slope drift
        -- while the player reads the exit prompt. 3D traversal uses the normal CC.
        local dx=(keyDown('D') and 1 or 0)-(keyDown('A') and 1 or 0)
        self.paintX=math.max(-7.8,math.min(7.8,self.paintX+dx*2.8*dt))
        local ground=physics:raycast(v(self.paintX,8,36),v(0,-1,0),12)
        if not ground.hit then reset(self);return end
        physics:move(self.body,0,0);setpos(self,{self.paintX,ground.point.y+.905,36})
        self.walker.transform.position=v(self.paintX,ground.point.y,36)
        text(self,'Hint',self.paintX>7.35 and '右端に着いた。 E  額縁を抜け、立体に戻る' or 'あなたは絵の中にいる。 D  右へ歩き、向こう側へ')
        keys='A / D  絵の中を歩く   E  右端から絵を出る   R  入り口に戻る'
        if keyPressed('E') and self.paintX>7.35 then
            self.paint=true;self.mode='leave';self.anim=0;self.yaw=0;self.pitch=0;sound();log('GALLERY painting crossed')
        end
    elseif self.mode=='leave' then
        self.anim=self.anim+dt/1.5;local t=smooth(self.anim)
        self.cam.transform.position=v(p.x*t,4.5+(p.y+.8-4.5)*t,18+(p.z-18)*t);self.cam.transform.rotation=v(0,0,0);self.cam:setFov(55+13*t)
        self.walker.transform.scale=v(1-t,1-t,1-t)
        if self.anim>=1 then self.mode='walk';self.walker.transform.position=v(0,-50,0);self.walker.transform.scale=v(1,1,1) end
    elseif self.mode=='stair' then
        self.anim=self.anim+dt/3;local t=smooth(self.anim)
        find('CeilingStair').transform.rotation=v(0,0,180*(1-t))
        self.pitch=20*(1-t);firstcamera(self)
        text(self,'Hint','上と下がつながる。天井の階段が、足元へ降りる')
        if self.anim>=1 then staircolliders(true);self.stair=true;self.mode='walk';log('GALLERY ceiling connected') end
    end
    if self.stair and p.z>86 and p.y>6 and math.abs(p.x)<2.5 then
        if not self.complete then self.complete=true;self.mode='complete';input:setMouseCapture(false);sound();log('GALLERY COMPLETE: all 3 connections traversed') end
        text(self,'Chapter','JUNCTION / つながった世界')
        text(self,'Hint','穴を縫い、絵を歩き、天井を渡った。三つのつながりで出口へ')
        keys='クリア   Enter  もう一度遊ぶ'
        if keyPressed('ENTER') then loadScene('scenes/stagedemo3.json') end
    end
    text(self,'Keys',keys)
    saveNum('gallery_seam',self.seam and 1 or 0);saveNum('gallery_paint',self.paint and 1 or 0);saveNum('gallery_stair',self.stair and 1 or 0)
    saveNum('gallery_ready',self.ready and 1 or 0);saveNum('gallery_complete',self.complete and 1 or 0)
    saveNum('gallery_mode',({walk=0,seam=1,enter=2,painting=3,leave=4,stair=5,complete=6})[self.mode] or -1)
end
