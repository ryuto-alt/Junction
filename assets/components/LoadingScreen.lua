-- Minimal game-side loading screen. Target scene assets are preloaded by TitleMenu.
local function centered(text, y, size, alpha)
    ui:text(SCREEN_W * 0.5 - #text * size * 0.29, y, text, size, 1, 1, 1, alpha)
end

function OnStart(self)
    self.time = 0
    self.transitionRequested = false
    -- Keep the screen visible long enough for the transition to read as intentional.
    self.minimumDisplay = 1.45
end

function OnUpdate(self, dt)
    self.time = self.time + dt
    local progress = math.min(self.time / 0.35, 1)
    local fade = progress * progress * (3 - 2 * progress)
    ui:rect(0, 0, SCREEN_W, SCREEN_H, 0, 0, 0, 1, 0)

    local cx, cy = SCREEN_W * 0.5, SCREEN_H * 0.5 - 8
    local radius = 39
    local head = math.floor(self.time * 12) % 12
    for i = 0, 11 do
        local angle = (i / 12) * math.pi * 2 - math.pi * 0.5
        local x = cx + math.cos(angle) * radius
        local y = cy + math.sin(angle) * radius
        local distance = (head - i + 12) % 12
        local alpha = 0.15 + (1 - distance / 12) * 0.85
        ui:rect(x - 5, y - 5, 10, 10, 1, 1, 1, alpha * fade, 5)
    end

    centered("LOADING", cy + 74, 18, 0.78 * fade)
    if self.time >= self.minimumDisplay and not self.transitionRequested then
        self.transitionRequested = true
        fadeToScene("scenes/stagedemo1.json", 0.5)
    end
end
