-- Hinged interaction for the original doorleaf.gltf. Its local origin is the hinge.
local MOUSE_LEFT = 0x01
local REACH = 4.0
local OPEN_SPEED = 8.0

local function direction(yaw, pitch)
    local y, p = math.rad(yaw), math.rad(pitch)
    local cp = math.cos(p)
    return math.sin(y) * cp, math.sin(p), math.cos(y) * cp
end

local function quatFromYaw(yaw)
    local half = math.rad(yaw) * 0.5
    return { x = 0, y = math.sin(half), z = 0, w = math.cos(half) }
end

local function quatSlerp(a, b, t)
    local dot = a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w
    if dot < 0 then dot = -dot; b = { x = -b.x, y = -b.y, z = -b.z, w = -b.w } end
    if dot > 0.9995 then
        local q = { x = a.x + (b.x - a.x) * t, y = a.y + (b.y - a.y) * t,
                    z = a.z + (b.z - a.z) * t, w = a.w + (b.w - a.w) * t }
        local length = math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w)
        return { x = q.x / length, y = q.y / length, z = q.z / length, w = q.w / length }
    end
    local theta = math.acos(math.max(-1, math.min(1, dot)))
    local wa = math.sin((1 - t) * theta) / math.sin(theta)
    local wb = math.sin(t * theta) / math.sin(theta)
    return { x = a.x * wa + b.x * wb, y = a.y * wa + b.y * wb,
             z = a.z * wa + b.z * wb, w = a.w * wa + b.w * wb }
end

local function yawFromQuat(q)
    return math.deg(math.atan(2 * (q.w * q.y + q.x * q.z), 1 - 2 * (q.y * q.y + q.z * q.z)))
end

local function isTarget(self)
    local cam = scene:findEntity("MainCamera")
    if not (cam and cam:isValid()) then return false end
    local yaw = loadNum("camYaw", cam.transform.rotation.y)
    local pitch = loadNum("camPitch", 0)
    local dx, dy, dz = direction(yaw, pitch)
    local rad = math.rad(self.currentYaw)
    local rx, rz = math.cos(rad), -math.sin(rad)
    local cx = self.hingeX + rx * self.halfWidth
    local cz = self.hingeZ + rz * self.halfWidth
    local nx, nz = math.sin(self.currentYaw * math.pi / 180), math.cos(self.currentYaw * math.pi / 180)
    local denom = dx * nx + dz * nz
    if math.abs(denom) < 0.001 then return false end
    local origin = cam.transform.position
    local t = ((cx - origin.x) * nx + (cz - origin.z) * nz) / denom
    if t <= 0 or t > REACH then return false end
    local px, py, pz = origin.x + dx * t, origin.y + dy * t, origin.z + dz * t
    local across = (px - cx) * rx + (pz - cz) * rz
    return math.abs(across) <= self.halfWidth and py >= self.baseY and py <= self.baseY + self.height
end

function OnStart(self)
    local scale = self.transform.scale
    self.halfWidth = 0.95 * scale.x
    self.height = 2.52 * scale.y
    self.baseY = self.transform.position.y
    self.hingeX, self.hingeZ = self.transform.position.x, self.transform.position.z
    self.closedYaw = self.transform.rotation.y
    self.closedQuat = quatFromYaw(self.closedYaw)
    self.openQuat = quatFromYaw(self.closedYaw + 90)
    self.currentYaw, self.open, self.amount, self.mouseWasDown = self.closedYaw, false, 0, false
end

function OnUpdate(self, dt)
    local targeted = isTarget(self)
    if targeted then
        local x, y = SCREEN_W * 0.5, SCREEN_H * 0.5
        ui:rect(x - 12, y - 12, 24, 24, 0.0, 0.08, 0.06, 0.92, 12)
        ui:rect(x - 7, y - 7, 14, 14, 0.12, 1.0, 0.56, 1.0, 7)
    end
    local mouseDown = input:isKeyDown(MOUSE_LEFT) or input:isAsyncKeyDown(MOUSE_LEFT)
    if mouseDown and not self.mouseWasDown and targeted then self.open = not self.open end
    self.mouseWasDown = mouseDown
    local target = self.open and 1 or 0
    self.amount = self.amount + (target - self.amount) * math.min(1, dt * OPEN_SPEED)
    local q = quatSlerp(self.closedQuat, self.openQuat, self.amount)
    self.currentYaw = yawFromQuat(q)
    self.transform.rotation = Vec3.new(0, self.currentYaw, 0)
end
