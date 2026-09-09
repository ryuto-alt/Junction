-- JUNCTION title-screen demo. The room remains a real 3D scene behind the UI.
local function clamp(v, lo, hi)
    return math.max(lo, math.min(hi, v))
end

local function smooth(current, target, speed, dt)
    return current + (target - current) * (1 - math.exp(-speed * dt))
end

local function centered(text, y, size, r, g, b, a)
    -- The bundled UI font is proportional; this is a deliberately conservative title/menu centering estimate.
    ui:text(SCREEN_W * 0.5 - #text * size * 0.29, y, text, size, r, g, b, a)
end

function OnStart(self)
    self.time = 0
    self.selection = 1
    self.starting = false
    self.preloadRequested = false
    self.titleIn = 0
    self.menuIn = 0
    self.buttonScale = { 1, 1 }
    self.stickDirection = 0
    input:setMouseCapture(false)

    -- Keep the room readable: the near light stays on, the far one is off,
    -- and only the middle light is allowed to flicker.
    local flickerLight = scene:findEntity("TitleLight_2")
    if flickerLight and flickerLight:isValid() and flickerLight:light() then
        Flicker(flickerLight:light(), "fluorescent")
    end
    pcall(function() audio:playSFXId("audio/amb/hum.wav", true, 0.22) end)
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    self.titleIn = smooth(self.titleIn, 1, 2.9, dt)
    self.menuIn = smooth(self.menuIn, self.time > 0.55 and 1 or 0, 5.4, dt)

    if keyPressed("DOWN") or keyPressed("S") or padPressed("DPAD_DOWN") then self.selection = 2 end
    if keyPressed("UP") or keyPressed("W") or padPressed("DPAD_UP") then self.selection = 1 end
    local _, stickY = padStick("left")
    local direction = stickY > 0.65 and 1 or (stickY < -0.65 and -1 or 0)
    if direction ~= 0 and self.stickDirection == 0 then
        self.selection = direction > 0 and 1 or 2
    end
    self.stickDirection = direction

    local buttonW, buttonH = 278, 58
    local buttonX = SCREEN_W * 0.5 - buttonW * 0.5
    local startY, quitY = SCREEN_H * 0.62, SCREEN_H * 0.62 + 76
    -- The stock button is only the hit target. Inset it so its square fallback
    -- never peeks out at the rounded neon frame's corners.
    -- IDs must be distinct: duplicate empty labels make ImGui report the same click for both buttons.
    local startClick = ui:button(buttonX + 3, startY + 3, buttonW - 6, buttonH - 6, "##title_start")
    local quitClick = ui:button(buttonX + 3, quitY + 3, buttonW - 6, buttonH - 6, "##title_quit")
    if startClick then self.selection = 1 end
    if quitClick then self.selection = 2 end

    local confirm = keyPressed("ENTER") or keyPressed("SPACE") or padPressed("A") or startClick or quitClick
    if confirm and not self.starting then
        if self.selection == 1 then
            self.starting = true
            self.startT = 0
        else
            quit()
            return
        end
    end

    -- A dark film keeps the moving, fluorescent-lit room legible without hiding it.
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.025, 0.035, 0.028, 0.38, 0)
    local titleAlpha = clamp(self.titleIn * 1.22, 0, 1)
    local titleY = SCREEN_H * 0.25 + (1 - self.titleIn) * 34
    centered("JUNCTION", titleY + 4, 84, 0.01, 0.02, 0.01, titleAlpha * 0.72)
    centered("JUNCTION", titleY, 84, 0.94, 0.98, 0.92, titleAlpha)

    for i, spec in ipairs({ { "START", startY }, { "QUIT", quitY } }) do
        local active = self.selection == i
        -- Keep the custom frame just beyond the stock hit target even while inactive.
        local targetScale = active and (1.055 + math.sin(self.time * 5.2) * 0.012) or 1.025
        self.buttonScale[i] = smooth(self.buttonScale[i], targetScale, 11, dt)
        local scale = self.buttonScale[i] * self.menuIn
        local w, h = buttonW * scale, buttonH * scale
        local x, y = SCREEN_W * 0.5 - w * 0.5, spec[2] + (buttonH - h) * 0.5
        local edge = active and 0.96 or 0.58
        local textLight = active and 0.96 or 0.82
        -- Outer glow, then a solid neon frame and finally the opaque black face.
        ui:rect(x - 3, y - 3, w + 6, h + 6, 0.16, 0.95, 0.43, active and 0.22 or 0.08, 18)
        ui:rect(x, y, w, h, 0.12, 0.94, 0.40, edge * self.menuIn, 15)
        ui:rect(x + 3, y + 3, w - 6, h - 6, 0.004, 0.008, 0.005, 0.96 * self.menuIn, 12)
        centered(spec[1], y + h * 0.27, 23 * scale, textLight, 1.0, 0.88, self.menuIn)
    end

    if self.starting then
        self.startT = self.startT + dt
        if not self.preloadRequested then
            self.preloadRequested = true
            preloadScene("scenes/stagedemo3.json")
        end
        ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.01, 0.02, 0.012, clamp(self.startT * 2.6, 0, 1), 0)
        if self.startT > 0.45 then loadScene("scenes/loading_demo.json") end
    end
end
