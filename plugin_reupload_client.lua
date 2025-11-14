-- plugin_reupload_client.lua
-- Run in Studio (CommandBar or plugin). Requires HttpService enabled for Studio.
local HttpService = game:GetService("HttpService")
local SelectionService = game:GetService("Selection") -- for plugin environment, or just workspace scanning
local Players = game:GetService("Players")

-- Simple UI using ScreenGui (works as LocalScript / CommandBar; in plugin you can create DockWidget)
local function create(class, props)
	local o = Instance.new(class)
	if props then
		for k,v in pairs(props) do
			if k == "Parent" then o.Parent = v else pcall(function() o[k] = v end) end
		end
	end
	return o
end

-- parent: if plugin environment supports CoreGui protection, choose accordingly; otherwise PlayerGui
local parent = game:GetService("CoreGui")
-- create UI
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

-- list frame
local listFrame = create("ScrollingFrame", {Parent = main, Size = UDim2.new(1,-20,0,120), Position = UDim2.new(0,10,0,190), BackgroundColor3 = Color3.fromRGB(20,20,22)})
local uiList = create("UIListLayout", {Parent = listFrame, Padding = UDim.new(0,4)})
uiList.SortOrder = Enum.SortOrder.LayoutOrder

local collected = {}  -- { {instance=Instance, oldId=number, name=string, type="Animation" } }

local function stripAssetId(str)
	if not str then return nil end
	-- e.g. "rbxassetid://12345678" or "rbxasset://textures/whatever"
	local num = tostring(str):match("(%d+)")
	if num then return tonumber(num) end
	return nil
end

local function scanWorkspaceFor(tab)
	collected = {}
	-- search Workspace and descendants (and also ServerStorage/ReplicatedStorage if needed)
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
	-- show preview first 30
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


-- =================================================================
-- [NEW] ฟังก์ชันสำหรับส่งทีละรายการ
-- =================================================================
local function sendSingleToServer(port, item)
	local url = ("http://127.0.0.1:%s/api/reupload_single"):format(tostring(port))
	
	-- สร้าง payload เฉพาะข้อมูลที่จำเป็น (ไม่ส่ง 'instance')
	local payload = {
		oldId = item.oldId,
		name = item.name,
		type = item.type
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

-- =================================================================
-- [NEW] ฟังก์ชันสำหรับอัปเดตทีละรายการ
-- =================================================================
local function applySingleResult(result)
	local oldId = result.oldId
	local newId = result.newId
	local status = result.status
	
	if status ~= "ok" or not newId then
		statusLabel.Text = string.format("Failed to update %d: %s", oldId, result.error or "Unknown error")
		return
	end
	
	-- ค้นหา instance ที่ตรงกันในตาราง 'collected'
	local foundInstance = nil
	for _, ent in ipairs(collected) do
		if ent.oldId == oldId then
			-- เจอแล้ว, ทำการอัปเดต
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
				break -- หยุดค้นหา
			end
		end
	end
	
	if foundInstance then
		statusLabel.Text = string.format("Updated: %s (%d -> %d)", foundInstance.Name, oldId, newId)
	else
		-- สิ่งนี้ไม่ควรเกิดขึ้นถ้าการสแกนถูกต้อง
		statusLabel.Text = string.format("Completed %d -> %d (Instance not found?)", oldId, newId)
	end
end


-- =================================================================
-- [REPLACED] แก้ไข Logic การทำงานของปุ่ม Start
-- =================================================================
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

	-- ปิดปุ่มเพื่อป้องกันการกดซ้ำ
	startBtn.Text = "Running..."
	startBtn.Enabled = false

	-- รันใน Thread ใหม่ (coroutine) เพื่อไม่ให้ UI ค้าง
	task.spawn(function()
		local successCount = 0
		local failCount = 0
		
		-- วน Loop ทีละรายการในตารางที่สแกนมา
		for i, item in ipairs(collected) do
			statusLabel.Text = string.format("Processing %d/%d... (%s)", i, #collected, item.name)
			
			-- 1. ส่ง Request ไปที่ Server
			local result, err = sendSingleToServer(port, item)
			
			if not result then
				-- ถ้า Server มีปัญหา
				statusLabel.Text = string.format("Error on %d: %s", item.oldId, tostring(err))
				failCount = failCount + 1
			else
				-- 2. Server ตอบกลับมา, ทำการอัปเดต ID
				applySingleResult(result)
				
				if result.status == "ok" then
					successCount = successCount + 1
				else
					failCount = failCount + 1
				end
			end
			
			-- 3. หน่วงเวลาก่อนส่งรายการถัดไป (ป้องกัน Rate Limit)
			task.wait(0.5) 
		end
		
		-- Loop จบแล้ว
		statusLabel.Text = string.format("Status: Completed. %d successful, %d failed.", successCount, failCount)
		startBtn.Text = "Start"
		startBtn.Enabled = true
	end)
end)

print("[ReuploaderPluginUI] Loaded. Set port to server and press Scan -> Start.")
