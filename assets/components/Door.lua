-- Stage 2 hinged door interaction. Attach this to each Door mesh entity.
local MOUSE_LEFT = 0x01
local REACH = 4.0
local OPEN_SPEED = 8.0

local function drawInteractReticle()
    local x, y = SCREEN_W * 0.5, SCREEN_H * 0.5
    ui:rect(x - 12, y - 12, 24, 24, 0.0, 0.08, 0.06, 0.92, 12)
    ui:rect(x - 7, y - 7, 14, 14, 0.12, 1.0, 0.56, 1.0, 7)
end

local function direction(yaw, pitch)
    local y = math.rad(yaw)
    local p = math.rad(pitch)
    local cp = math.cos(p)
    return math.sin(y) * cp, math.sin(p), math.cos(y) * cp
end

local function isTarget(self)
    local cam = scene:findEntity("MainCamera")
    if not (cam and cam:isValid()) then return false end

    local yaw = loadNum("camYaw", cam.transform.rotation.y)
    local pitch = loadNum("camPitch", 0)
    local dx, dy, dz = direction(yaw, pitch)
    local yawRad = math.rad(self.currentYaw)
    local nx, nz = math.sin(yawRad), math.cos(yawRad)
    local denom = dx * nx + dz * nz
    if math.abs(denom) < 0.001 then return false end

    local origin = cam.transform.position
    local center = self.transform.position
    local t = ((center.x - origin.x) * nx + (center.z - origin.z) * nz) / denom
    if t <= 0 or t > REACH then return false end

    local px = origin.x + dx * t
    local py = origin.y + dy * t
    local pz = origin.z + dz * t
    local rx, rz = math.cos(yawRad), -math.sin(yawRad)
    local across = (px - center.x) * rx + (pz - center.z) * rz
    if math.abs(across) > self.halfWidth or py < self.baseY or py > self.baseY + self.height then return false end

    return true
end

local ROOM_INTERIOR = {
    A_Leaf_s1a = { 0, 0 },
    A_Leaf_f1 = { 0, 0 },
    A_Leaf_s2a = { 0, 0 },
    P_Leaf_s1b = { 0, 22 },
    Q_Leaf_s2b = { 13, 0 }
}

local function openingAngleTowardRoom(self)
    local room = ROOM_INTERIOR[self.name]
    if not room then return -90 end

    local closed = math.rad(self.closedYaw)
    local cx = self.hingeX - math.cos(closed) * self.halfWidth
    local cz = self.hingeZ + math.sin(closed) * self.halfWidth
    local toRoomX, toRoomZ = room[1] - cx, room[2] - cz

    local function score(angle)
        local yaw = math.rad(self.closedYaw + angle)
        local x = self.hingeX - math.cos(yaw) * self.halfWidth
        local z = self.hingeZ + math.sin(yaw) * self.halfWidth
        return (x - cx) * toRoomX + (z - cz) * toRoomZ
    end

    -- トンネル側の側壁を避け、必ず所属する部屋の内側へ開く。
    return score(90) >= score(-90) and 90 or -90
end

function OnStart(self)
    local scale = self.transform.scale
    self.halfWidth = scale.x
    self.height = 4.025465965270996 * scale.y
    self.baseY = self.transform.position.y
    self.closedYaw = self.transform.rotation.y
    self.openAngle = 90

    local yaw = math.rad(self.closedYaw)
    -- door.gltf の原点は中央。蝶番はローカル +X 側にある。
    self.hingeX = self.transform.position.x + math.cos(yaw) * self.halfWidth
    self.hingeZ = self.transform.position.z - math.sin(yaw) * self.halfWidth
    self.open = false
    self.amount = 0
    self.currentYaw = self.closedYaw
    self.mouseWasDown = false
end

function OnUpdate(self, dt)
    local targeted = isTarget(self)
    if targeted then drawInteractReticle() end

    -- マウスキャプチャ時も確実に拾えるよう、入力キューと OS 状態を併用する。
    local mouseDown = input:isKeyDown(MOUSE_LEFT) or input:isAsyncKeyDown(MOUSE_LEFT)
    if mouseDown and not self.mouseWasDown and targeted then
        if not self.open then
            self.openAngle = openingAngleTowardRoom(self)
        end
        self.open = not self.open
    end
    self.mouseWasDown = mouseDown

    local target = self.open and 1 or 0
    self.amount = self.amount + (target - self.amount) * math.min(1, dt * OPEN_SPEED)
    local yaw = self.closedYaw + self.openAngle * self.amount
    local rad = math.rad(yaw)
    self.currentYaw = yaw
    self.transform.position = Vec3.new(self.hingeX - math.cos(rad) * self.halfWidth, self.baseY,
                                       self.hingeZ + math.sin(rad) * self.halfWidth)
    self.transform.rotation = Vec3.new(0, yaw, 0)
end
