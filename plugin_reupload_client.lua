-- plugin_reupload_client.lua
-- (อัปเดต: แก้ไข CheckBox -> TextCheckBox)
local HttpService = game:GetService("HttpService")
local SelectionService = game:GetService("Selection")
local Players = game:GetService("Players")

local function create(class, props)
	local o = Instance.new(class)
	if props then
		for k,v in pairs(props) do
			if k == "Parent" then o.Parent = v else pcall(function() o[k] = v end) end
		end
	end
	return o
end

local parent = game:GetService("CoreGui")
local gui = create("ScreenGui", {Name = "ReuploaderPluginUI", Parent = parent, ResetOnSpawn = false})
local main = create("Frame", {Parent = gui, Size = UDim2.new(0,420,0,320), Position = UDim2.new(0.3,0,0.2,0), BackgroundColor3 = Color3.fromRGB(30,30,32)})
create("UICorner", {Parent = main, CornerRadius = UDim.new(0,8)})
local title = create("TextLabel", {Parent = main, Text = "Reuploader Plugin UI", Size = UDim2.new(1,0,0,36), BackgroundTransparency = 1, TextColor3 = Color3.new(1,1,1), Font = Enum.Font.SourceSansBold, TextSize = 18})

-- Tabs (Animation, Sound)
local tabAnim = create("TextButton", {Parent = main, Text = "Animation", Size = UDim2.new(0.48, -6, 0, 30), Position = UDim2.new(0.02,0,0,42)})
local tabSound = create("TextButton", {Parent = main, Text = "Sound", Size = UDim2.new(0.48, -6, 0, 30), Position = UDim2.new(0.5,6,0,42)})
local currentTab = "Animation"
tabAnim.MouseButton1Click:Connect(function() currentTab = "Animation"; tabAnim.BackgroundColor3 = Color3.fromRGB(70,70,72); tabSound.BackgroundColor3 = Color3.fromRGB(45,45,47) end)
tabSound.MouseButton1Click:Connect(function() currentTab = "Sound"; tabSound.BackgroundColor3 = Color3.fromRGB(70,70,72); tabAnim.BackgroundColor3 = Color3.fromRGB(45,45,47) end)
tabAnim.BackgroundColor3 = Color3.fromRGB(70,70,72)

-- port input and control
local portBox = create("TextBox", {Parent = main, PlaceholderText = "Enter server port (e.g. 34567)", Size = UDim2.new(0.66,0,0,26), Position = UDim2.new(0.02,0,0,84), BackgroundColor3 = Color3.fromRGB(40,40,42), TextColor3 = Color3.new(1,1,1)})
local scanBtn = create("TextButton", {Parent = main, Text = "Scan", Size = UDim2.new(0.32,0,0,26), Position = UDim2.new(0.70,0,0,84), BackgroundColor3 = Color3.fromRGB(60,60,62)})
local startBtn = create("TextButton", {Parent = main, Text = "Start", Size = UDim2.new(0.48,0,0,28), Position = UDim2.new(0.02,0,0,122), BackgroundColor3 = Color3.fromRGB(60,120,60)})
local statusLabel = create("TextLabel", {Parent = main, Text = "Status: Idle", Size = UDim2.new(1,0,0,24), Position = UDim2.new(0,0,0,160), BackgroundTransparency = 1, TextColor3 = Color3.new(1,1,1)})

-- =================================================================
-- [FIXED] แก้ไข CheckBox เป็น TextCheckBox
-- =================================================================
local checkExistingBox = create("TextCheckBox", {
	Parent = main,
	Text = "ตรวจสอบของเก่า (ช้า)",
	TextColor3 = Color3.new(1,1,1),
	Size = UDim2.new(0.48, 0, 0, 28),
	Position = UDim2.new(0.5, 6, 0, 122),
	Checked = false -- ค่าเริ่มต้นคือ 'ปิด' (เพื่อความเร็ว)
})
-- =================================================================

-- list frame
local listFrame = create("ScrollingFrame", {Parent = main, Size = UDim2.new(1,-20,0,120), Position = UDim2.new(0,10,0,190), BackgroundColor3 = Color3.fromRGB(20,20,22)})
local uiList = create("UIListLayout", {Parent = listFrame, Padding = UDim.new(0,4)})
uiList.SortOrder = Enum.SortOrder.LayoutOrder

local collected = {}  -- { {instance=Instance, oldId=number, name=string, type="Animation" } }

local function stripAssetId(str)
	if not str then return nil end
	local num = tostring(str):match("(%d+)")
	if num then return tonumber(num) end
	return nil
end

local function scanWorkspaceFor(tab)
	collected = {}
	local containers = {workspace, game:GetService("ReplicatedStorage"), game:GetService("ServerStorage")}
	for _, root in ipairs(containers) do
		for _, inst in ipairs(root:GetDescendants()) do
			if tab == "Animation" then
				if inst:IsA("Animation") then
					local aid = stripAssetId(inst.AnimationId)
					if aid then table.insert(collected, {instance = inst, oldId = aid, name = inst.Name, type = "Animation"}) end
				end
			elseif tab == "Sound" then
				if inst:IsA("Sound") then
					local sid = stripAssetId(inst.SoundId)
					if sid then table.insert(collected, {instance = inst, oldId = sid, name = inst.Name, type = "Sound"}) end
				end
			end
		end
	end
	
	statusLabel.Text = "Status: Found " .. tostring(#collected) .. " items."
	for _,c in ipairs(listFrame:GetChildren()) do
		if c:IsA("TextLabel") then c:Destroy() end
	end
	for i = 1, math.min(#collected, 30) do
		local ent = collected[i]
		create("TextLabel", {Parent = listFrame, Size = UDim2.new(1,-10,0,18), BackgroundTransparency = 1, Text = string.format("[%d] %s -> %d", i, ent.name, ent.oldId), TextColor3 = Color3.new(1,1,1), TextXAlignment = Enum.TextXAlignment.Left})
	end
end

scanBtn.MouseButton1Click:Connect(function()
	scanWorkspaceFor(currentTab)
end)


local function sendSingleToServer(port, item, checkExisting)
	local url = ("http://127.0.0.1:%s/api/reupload_single"):format(tostring(port))
	
	local payload = {
		oldId = item.oldId,
		name = item.name,
		type = item.type,
		check_existing = checkExisting 
	}
	local body = HttpService:JSONEncode(payload)
	
	statusLabel.Text = string.format("Sending: %s (%d)", item.name, item.oldId)
	
	local ok, res = pcall(function()
		return HttpService:PostAsync(url, body, Enum.HttpContentType.ApplicationJson)
	end)
	
	if not ok then
		statusLabel.Text = "Status: Error contacting server: " .. tostring(res)
		return nil, res
	end
	
	local decoded, decodeErr = pcall(HttpService.JSONDecode, HttpService, res)
	if not decoded then
		statusLabel.Text = "Status: Error decoding server response: " .. tostring(decodeErr)
		return nil, decodeErr
	end
	
	return decoded, nil
end

local function applySingleResult(result)
	local oldId = result.oldId
	local newId = result.newId
	local status = result.status
	
	if status ~= "ok" or not newId then
		statusLabel.Text = string.format("Failed to update %d: %s", oldId, result.error or "Unknown error")
		return
	end
	
	local foundInstance = nil
	for _, ent in ipairs(collected) do
		if ent.oldId == oldId then
			pcall(function()
				if ent.type == "Animation" and ent.instance and ent.instance:IsA("Animation") then
					ent.instance.AnimationId = "rbxassetid://" .. tostring(newId)
					foundInstance = ent.instance
				elseif ent.type == "Sound" and ent.instance and ent.instance:IsA("Sound") then
					ent.instance.SoundId = "rbxassetid://" .. tostring(newId)
					foundInstance = ent.instance
				end
			end)
			if foundInstance then
				break
			end
		end
	end
	
	if result.skipped then
		statusLabel.Text = string.format("Skipped (found): %s (%d -> %d)", foundInstance.Name, oldId, newId)
	elseif foundInstance then
		statusLabel.Text = string.format("Updated: %s (%d -> %d)", foundInstance.Name, oldId, newId)
	else
		statusLabel.Text = string.format("Completed %d -> %d (Instance not found?)", oldId, newId)
	end
end

startBtn.MouseButton1Click:Connect(function()
	local port = tonumber(portBox.Text)
	if not port then
		statusLabel.Text = "Status: Invalid port"
		return
	end
	
	if #collected == 0 then
		statusLabel.Text = "Status: No items found (press Scan first)"
		return
	end

	local shouldCheckExisting = checkExistingBox.Checked

	startBtn.Text = "Running..."
	startBtn.Enabled = false
	checkExistingBox.Enabled = false

	task.spawn(function()
		local successCount = 0
		local failCount = 0
		
		for i, item in ipairs(collected) do
			statusLabel.Text = string.format("Processing %d/%d... (%s)", i, #collected, item.name)
			
			local result, err = sendSingleToServer(port, item, shouldCheckExisting)
			
			if not result then
				statusLabel.Text = string.format("Error on %d: %s", item.oldId, tostring(err))
				failCount = failCount + 1
			else
				applySingleResult(result)
				
				if result.status == "ok" then
					successCount = successCount + 1
				else
					failCount = failCount + 1
				end
			end
			
			task.wait(0.2) 
		end
		
		statusLabel.Text = string.format("Status: Completed. %d successful, %d failed.", successCount, failCount)
		startBtn.Text = "Start"
		startBtn.Enabled = true
		checkExistingBox.Enabled = true
	end)
end)

print("[ReuploaderPluginUI] Loaded. Set port to server and press Scan -> Start.")
