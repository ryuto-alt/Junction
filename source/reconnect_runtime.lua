-- RECONNECT runtime. Only the explicitly requested E action commits a connection.
-- No adaptation/afterimage assumptions, timed crossings or center-screen gauges.
local function find(name)
    local e=scene:findEntity(name)
    assert(e and e:isValid(), 'RECONNECT missing entity: '..name)
    return e
end
local function vec(a) return Vec3.new(a[1],a[2],a[3]) end
local function dist(a,b)
    local x,y,z=a[1]-b[1],a[2]-b[2],a[3]-b[3]
    return math.sqrt(x*x+y*y+z*z)
end
local function dotray(eye,a,b)
    local ax,ay,az=a[1]-eye.x,a[2]-eye.y,a[3]-eye.z
    local bx,by,bz=b[1]-eye.x,b[2]-eye.y,b[3]-eye.z
    local d=math.sqrt((ax*ax+ay*ay+az*az)*(bx*bx+by*by+bz*bz))
    if d<.00001 then return 180 end
    return math.deg(math.acos(math.max(-1,math.min(1,(ax*bx+ay*by+az*bz)/d))))
end
local function hud(self,key,text)
    if self.text[key]~=text then
        scene:setUiText(self.ui[key],text);self.text[key]=text
    end
end
local function sound(name,vol) audio:playSFXId('audio/ui/'..name..'.wav',false,vol or .55) end
local function teleport(self,cp)
    physics:setPosition(self.body,vec(cp));self.yaw=0;self.pitch=0
end
local function drawparts(p,t)
    for _,part in ipairs(p.parts) do
        local k=part.k+(1-part.k)*t
        part.e.transform.position=Vec3.new(p.eye[1]+(part.target[1]-p.eye[1])*k,
            p.eye[2]+(part.target[2]-p.eye[2])*k,p.eye[3]+(part.target[3]-p.eye[3])*k)
        part.e.transform.scale=Vec3.new(k,k,k)
    end
    for _,b in ipairs(p.beads) do
        local k=b.k+(1-b.k)*t
        b.e.transform.position=Vec3.new(p.eye[1]+(b.target[1]-p.eye[1])*k,
            p.eye[2]+(b.target[2]-p.eye[2])*k,p.eye[3]+(b.target[3]-p.eye[3])*k)
    end
end

function OnStart(self)
    self.body=find('ReconnectPlayer');self.cam=find('ReconnectCamera')
    self.ui={Chapter=find('HUD_Chapter'),Hint=find('HUD_Hint'),Keys=find('HUD_Keys')}
    self.text={};self.yaw=0;self.pitch=0;self.elapsed=0;self.step=0
    self.active=1;self.solved=0;self.checkpoint={-2,.91,-5};self.checkIndex=0
    self.message='';self.messageTime=0;self.readyTime=0;self.complete=false;self.gate=find('ExitGate')
    self.doorY=5.7;self.debugLock=false
    -- Scene-independent memory is telemetry only; never progression authority.
    for _,k in ipairs({'solved','ready','complete','error','active'}) do saveNum('reconnect_'..k,0) end
    for _,p in ipairs(PUZZLES) do
        p.done=false;p.anim=nil;p.tint=-1
        for _,part in ipairs(p.parts) do
            part.e=find(part.root);part.c=find(part.collider)
            part.c.transform.position=Vec3.new(part.target[1],part.target[2]-30,part.target[3])
        end
        for _,b in ipairs(p.beads) do b.e=find(b.name);scene:setMeshParams(b.e,.9,.42,.095,1) end
        for i,_ in ipairs(p.parts) do
            for _,side in ipairs({'-1','1'}) do scene:setMeshParams(find('P'..p.id..'_Edge'..i..'_'..side),.9,.42,.095,1) end
            scene:setMeshParams(find('P'..p.id..'_Spine'..i),.9,.42,.095,1)
        end
        drawparts(p,0)
    end
    input:setMouseCapture(true)
    self.gate.transform.position=Vec3.new(0,5.7,92)
    for _,x in ipairs({'-1.2','0','1.2'}) do find('ExitGateMark'..x).transform.position=Vec3.new(tonumber(x),5.7,91.84) end
    log('RECONNECT start: 4 explicit, persistent perspective connections')
end

function OnUpdate(self,dt)
    dt=math.min(dt,.08);self.elapsed=self.elapsed+dt
    if self.elapsed<.7 then teleport(self,{-2,.91,-5}) end
    if keyPressed('ESC') then input:setMouseCapture(not input:isMouseCaptured()) end
    if input:isMouseCaptured() and loadNum('reconnect_lockMouse',0)<.5 then
        self.yaw=self.yaw+input:getMouseDeltaX()*.085
        self.pitch=self.pitch-input:getMouseDeltaY()*.085
    end
    if keyDown('LEFT') then self.yaw=self.yaw-85*dt end
    if keyDown('RIGHT') then self.yaw=self.yaw+85*dt end
    if keyDown('UP') then self.pitch=self.pitch+70*dt end
    if keyDown('DOWN') then self.pitch=self.pitch-70*dt end
    -- Opt-in MCP camera fixture; never changes position, alignment or progress.
    -- Used to drive real WASD traversal reproducibly without desktop mouse noise.
    if loadNum('reconnect_testMode',0)>.5 then
        self.yaw=loadNum('reconnect_testYaw',0);self.pitch=loadNum('reconnect_testPitch',0)
    end
    self.yaw=self.yaw%360
    if self.complete then
        self.winTime=math.min(1,(self.winTime or 0)+dt/1.8)
        local t=self.winTime*self.winTime*(3-2*self.winTime)
        self.yaw=(self.winYaw+180*t)%360;self.pitch=-9*t
    end
    self.pitch=math.max(-78,math.min(78,self.pitch))
    local yaw,pitch=math.rad(self.yaw),math.rad(self.pitch)
    local fx,fz=math.sin(yaw),math.cos(yaw)
    local mx,mz=0,0
    if keyDown('W') then mx,mz=mx+fx,mz+fz end
    if keyDown('S') then mx,mz=mx-fx,mz-fz end
    if keyDown('A') then mx,mz=mx-fz,mz+fx end
    if keyDown('D') then mx,mz=mx+fz,mz-fx end
    local moving=math.sqrt(mx*mx+mz*mz)
    local animating=false
    for _,p in ipairs(PUZZLES) do if p.anim then animating=true end end
    if moving>0 and not animating and not self.complete then
        local speed=keyDown('SHIFT') and 4.5 or 3.4
        physics:move(self.body,mx/moving*speed,mz/moving*speed)
        self.step=self.step+dt
        if self.step>.48 and physics:isGrounded(self.body) then sound('step',.15);self.step=0 end
    else physics:move(self.body,0,0) end
    -- Jumping is deliberately not needed: this is a perspective walk, not a timing test.
    local pos=self.body.transform.position
    if pos.y < -3 or keyPressed('R') then
        teleport(self,self.checkpoint);pos=self.body.transform.position
        self.message='足場へ戻った。つないだ道は残っている';self.messageTime=3
        sound('touch',.3)
    end
    self.cam.transform.position=Vec3.new(pos.x,pos.y+.8,pos.z)
    self.cam.transform.rotation=Vec3.new(-self.pitch,self.yaw,0)
    local eye=self.cam.transform.position
    local p=PUZZLES[self.active]
    local ready=false;local error=180
    if p and not self.complete then
        local inzone=pos.z>=p.zone[1] and pos.z<=p.zone[2]
        if inzone and self.checkIndex<self.active and physics:isGrounded(self.body) then
            self.checkpoint=p.checkpoint;self.checkIndex=self.active
        end
        if inzone and not p.done and not p.anim and physics:isGrounded(self.body) then
            error=0
            for _,pair in ipairs(p.joins) do error=math.max(error,dotray(eye,pair[1],pair[2])) end
            -- All paired joints must be in the forward view. Rotation alone cannot solve parallax.
            for _,pair in ipairs(p.joins) do
                local q=pair[1]
                local dx,dy,dz=q[1]-eye.x,q[2]-eye.y,q[3]-eye.z
                local length=math.sqrt(dx*dx+dy*dy+dz*dz)
                local forward=(dx*fx*math.cos(pitch)+dy*math.sin(pitch)+dz*fz*math.cos(pitch))/math.max(.001,length)
                if forward<.70 then error=180 end
            end
            ready=error<=p.tol
            local tint=ready and 2 or (error<3 and 1 or 0)
            if p.tint~=tint then
                for _,b in ipairs(p.beads) do
                    if ready then scene:setMeshParams(b.e,.68,1,.72,1)
                    elseif tint==1 then scene:setMeshParams(b.e,1,.77,.28,1)
                    else scene:setMeshParams(b.e,.9,.42,.095,1) end
                end
                if ready then sound('detent',.38) end
                p.tint=tint
            end
            if keyPressed('E') then
                if ready then
                    p.anim=0;self.readyTime=0;sound('connect',.65)
                    log('RECONNECT commit '..p.id..' angularError='..string.format('%.4f',error))
                else
                    self.message='まだ線がずれている。向きより、立つ場所を変える'
                    self.messageTime=2.5;sound('deny',.2)
                end
            end
        end
        hud(self,'Chapter',p.title..'    '..self.solved..' / 4')
        local hint=p.help
        if ready then hint='線がつながった。E で道にする'
        elseif p.anim then hint='つないでいる'
        elseif pos.z<p.zone[1] then hint='つないだ道を渡って、次の金色の線へ' end
        hud(self,'Hint',hint)
    end
    for _,q in ipairs(PUZZLES) do
        if q.anim then
            q.anim=math.min(1,q.anim+dt/.85)
            local t=q.anim*q.anim*(3-2*q.anim)
            drawparts(q,t)
            if q.anim>=1 then
                for _,part in ipairs(q.parts) do part.c.transform.position=vec(part.solid) end
                for _,b in ipairs(q.beads) do scene:setMeshParams(b.e,.68,1,.72,1) end
                for i,_ in ipairs(q.parts) do
                    for _,side in ipairs({'-1','1'}) do scene:setMeshParams(find('P'..q.id..'_Edge'..i..'_'..side),.40,.84,.69,1) end
                    scene:setMeshParams(find('P'..q.id..'_Spine'..i),.40,.84,.69,1)
                end
                q.done=true;q.anim=nil;self.solved=self.solved+1;self.active=self.solved+1
                self.message='接続した。道はもう消えない';self.messageTime=3
                log('RECONNECT solid '..q.id)
            end
        end
    end
    if self.solved==4 then
        self.doorY=math.min(12,self.doorY+dt*3)
        self.gate.transform.position=Vec3.new(0,self.doorY,92)
        for _,x in ipairs({'-1.2','0','1.2'}) do find('ExitGateMark'..x).transform.position=Vec3.new(tonumber(x),self.doorY,91.84) end
        hud(self,'Chapter','JUNCTION / RECONNECT    4 / 4')
        hud(self,'Hint','上り道を渡り、光の枠の向こうへ')
        if pos.z>92.7 and pos.y>3.7 and not self.complete then
            self.complete=true;self.winYaw=self.yaw;self.winTime=0
            input:setMouseCapture(false);sound('clear',.6)
            log('RECONNECT complete: reached exit physically')
        end
    end
    if self.messageTime>0 then
        self.messageTime=self.messageTime-dt;hud(self,'Hint',self.message)
    end
    if self.complete then
        hud(self,'Chapter','JUNCTION / RECONNECT')
        hud(self,'Hint','離れていた道を、あなたの視点でつないだ。')
        hud(self,'Keys','接続完了    ENTER  もう一度遊ぶ    ESC  マウス解放')
        if keyPressed('ENTER') then loadScene('scenes/reconnect.json') end
    end
    saveNum('reconnect_solved',self.solved);saveNum('reconnect_ready',ready and 1 or 0)
    saveNum('reconnect_error',error);saveNum('reconnect_active',self.active)
    saveNum('reconnect_complete',self.complete and 1 or 0)
end
