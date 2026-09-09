-- JUNCTION clear screen. The dedicated scene looks from the facility toward daylight.
local function clamp(v, lo, hi)
    return math.max(lo, math.min(hi, v))
end

local function smooth(current, target, speed, dt)
    return current + (target - current) * (1 - math.exp(-speed * dt))
end

local function centered(text, y, size, r, g, b, a)
    ui:text(SCREEN_W * 0.5 - #text * size * 0.29, y, text, size, r, g, b, a)
end

local function drawTransition(t)
    local progress = clamp(t / 0.5, 0, 1)
    local alpha = progress * progress * (3 - 2 * progress)
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0, 0, 0, alpha, 0)
end

function OnStart(self)
    self.time = 0
    self.titleIn = 0
    self.menuIn = 0
    self.buttonScale = 1
    self.returning = false
    self.preloadRequested = false
    self.loadRequested = false
    input:setMouseCapture(false)

    local flickerLight = scene:findEntity("ClearLight_2")
    if flickerLight and flickerLight:isValid() and flickerLight:light() then
        Flicker(flickerLight:light(), "fluorescent")
    end
end

function OnUpdate(self, dt)
    local lamp = scene:findEntity("ClearLight_2")
    local panel = scene:findEntity("ClearLightPanel_2")
    if lamp:isValid() and panel:isValid() and lamp:light() then
        scene:setMeshParams(panel, 0.94, 0.98, 1.0, 1.15 * lamp:light().intensity / 5.8)
    end

    self.time = self.time + dt
    self.titleIn = smooth(self.titleIn, 1, 2.9, dt)
    self.menuIn = smooth(self.menuIn, self.time > 0.55 and 1 or 0, 5.4, dt)

    local buttonW, buttonH = 278, 58
    local buttonX = SCREEN_W * 0.5 - buttonW * 0.5
    local buttonY = SCREEN_H * 0.72
    local titleClick = not self.returning and
        ui:button(buttonX + 3, buttonY + 3, buttonW - 6, buttonH - 6, "##clear_title")
    local confirm = keyPressed("ENTER") or keyPressed("SPACE") or padPressed("A") or titleClick
    if confirm and not self.returning then
        self.returning = true
        self.returnT = 0
    end

    -- Retain detail in the dark corridor while keeping the daylight exit visible.
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0.018, 0.025, 0.022, 0.24, 0)
    local titleAlpha = clamp(self.titleIn * 1.22, 0, 1)
    local titleY = SCREEN_H * 0.17 + (1 - self.titleIn) * 34
    centered("CLEAR", titleY + 4, 84, 0.01, 0.02, 0.01, titleAlpha * 0.72)
    centered("CLEAR", titleY, 84, 0.94, 0.98, 0.92, titleAlpha)

    local targetScale = 1.055 + math.sin(self.time * 5.2) * 0.012
    self.buttonScale = smooth(self.buttonScale, targetScale, 11, dt)
    local scale = self.buttonScale * self.menuIn
    local w, h = buttonW * scale, buttonH * scale
    local x = SCREEN_W * 0.5 - w * 0.5
    local y = buttonY + (buttonH - h) * 0.5
    ui:rect(x - 3, y - 3, w + 6, h + 6, 0.16, 0.95, 0.43, 0.22 * self.menuIn, 18)
    ui:rect(x, y, w, h, 0.12, 0.94, 0.40, 0.96 * self.menuIn, 15)
    ui:rect(x + 3, y + 3, w - 6, h - 6, 0.004, 0.008, 0.005, 0.96 * self.menuIn, 12)
    centered("TITLE", y + h * 0.27, 23 * scale, 0.96, 1.0, 0.88, self.menuIn)

    if self.returning then
        self.returnT = self.returnT + dt
        drawTransition(self.returnT)
        if self.returnT >= 0.5 then
            if not self.preloadRequested then
                self.preloadRequested = true
            elseif not self.loadRequested then
                self.loadRequested = true
                preloadScene("scenes/title_demo.json")
                loadScene("scenes/title_demo.json")
            end
        end
    end
end
