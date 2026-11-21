-- Autotracking Archipelago : objets recus -> objets du pack, lieux coches -> sections de lieux, compteurs de commandes/paliers.
CUR_INDEX = -1
SEEN = {}
GOAL_EPISODE = 14
TOTALS = {}

local function find(code)
    return Tracker:FindObjectForCode(code)
end

local function set_counter(code, checked, total)
    local obj = find(code)
    if not obj then return end
    obj.Active = total > 0
    obj:SetOverlay(checked .. "/" .. total)
end

local function count_main()
    local checked, total = 0, 0
    for id, ep in pairs(ORDER_EPISODE) do
        if ep <= GOAL_EPISODE then
            total = total + 1
            if SEEN[id] then checked = checked + 1 end
        end
    end
    return checked, total
end

local function count_milestone(m)
    local total = TOTALS[m.code] or 0
    local checked = 0
    for n = 1, total do
        if SEEN[m.base + n] then checked = checked + 1 end
    end
    return checked, total
end

local function refresh_counters()
    local c, t = count_main()
    set_counter("ms_main", c, t)
    for _, m in ipairs(MILESTONES) do
        local mc, mt = count_milestone(m)
        set_counter(m.code, mc, mt)
    end
end

function onClear(slot_data)
    CUR_INDEX = -1
    SEEN = {}
    TOTALS = {}
    GOAL_EPISODE = 14
    for _, v in pairs(ITEM_MAPPING) do
        local obj = find(v[1])
        if obj then
            if v[2] == "consumable" then obj.AcquiredCount = 0 else obj.Active = false end
        end
    end
    for _, path in pairs(LOCATION_MAPPING) do
        local sec = find(path)
        if sec then sec.AvailableChestCount = sec.ChestCount end
    end
    if slot_data then
        GOAL_EPISODE = tonumber(slot_data["goal_episode"]) or 14
        local goal = find("goal14")
        if goal then goal.CurrentStage = (GOAL_EPISODE == 12) and 1 or 0 end
        for _, m in ipairs(MILESTONES) do
            TOTALS[m.code] = math.min(tonumber(slot_data[m.option]) or 0, m.max)
        end
    end
    refresh_counters()
end

function onItem(index, item_id, item_name, player_number)
    if index <= CUR_INDEX then return end
    CUR_INDEX = index
    local v = ITEM_MAPPING[item_id]
    if not v then return end
    local obj = find(v[1])
    if not obj then return end
    if v[2] == "consumable" then
        obj.AcquiredCount = obj.AcquiredCount + 1
    else
        obj.Active = true
    end
end

function onLocation(location_id, location_name)
    if SEEN[location_id] then return end
    SEEN[location_id] = true
    local path = LOCATION_MAPPING[location_id]
    if path then
        local sec = find(path)
        if sec then sec.AvailableChestCount = 0 end
    end
    refresh_counters()
end

Archipelago:AddClearHandler("ds clear handler", onClear)
Archipelago:AddItemHandler("ds item handler", onItem)
Archipelago:AddLocationHandler("ds location handler", onLocation)
