-- Pack PopTracker : Death Stranding (Archipelago)
ScriptHost:LoadScript("scripts/mapping.lua")
Tracker:AddItems("items/items.json")
Tracker:AddMaps("maps/maps.json")
Tracker:AddLocations("locations/locations.json")
Tracker:AddLayouts("layouts/tracker.json")

-- Remet les cases de commandes dans l'etat du serveur (SEEN, rempli par l'autotracking) : annule un clic droit fait par erreur.
-- Hors connexion (SEEN vide), tout est remis a « non fait ».
function resync_locations()
    local seen = SEEN or {}
    for id, path in pairs(LOCATION_MAPPING) do
        local sec = Tracker:FindObjectForCode(path)
        if sec then
            if seen[id] then sec.AvailableChestCount = 0 else sec.AvailableChestCount = sec.ChestCount end
        end
    end
    local vic = Tracker:FindObjectForCode(VICTORY_PATH)
    if vic then vic.AvailableChestCount = vic.ChestCount end
end

-- Bouton « Resync » (objet Lua) ; protege par pcall : s'il n'est pas disponible, le reste du pack fonctionne normalement.
local ok, err = pcall(function()
    local item = ScriptHost:CreateLuaItem()
    item.Name = "Resync with Archipelago (undo manual checks)"
    item.Icon = ImageReference:FromPackRelativePath("images/items/resync.png")
    item.CanProvideCodeFunc = function(self, code) return code == "resync" end
    item.ProvidesCodeFunc = function(self, code) if code == "resync" then return 1 end return 0 end
    item.OnLeftClickFunc = function(self) resync_locations() end
    item.OnRightClickFunc = function(self) resync_locations() end
end)
if not ok then print("Resync button unavailable: " .. tostring(err)) end

if PopVersion and Archipelago then
    ScriptHost:LoadScript("scripts/autotracking.lua")
end
