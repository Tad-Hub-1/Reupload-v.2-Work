-- plugin_reupload_client.lua
-- (Remake GUI: Modern Dark Theme + Draggable)

local HttpService = game:GetService("HttpService")
local UserInputService = game:GetService("UserInputService")
local RunService = game:GetService("RunService")

-- =================================================================
-- UI Theme Config (ตั้งค่าสีที่นี่)
-- =================================================================
local Theme = {
	MainBg = Color3.fromRGB(46, 46, 54),      -- สีพื้นหลังหลัก
	TitleBg = Color3.fromRGB(56, 56, 64),     -- สีแถบหัวข้อ
	ContainerBg = Color3.fromRGB(36, 36, 42), -- สีพื้นหลังช่อง Input/List
	AccentBlue = Color3.fromRGB(0, 170, 255), -- สีปุ่มหลัก (ฟ้า)
	AccentGreen = Color3.fromRGB(0, 200, 100),-- สีปุ่ม Start (เขียว)
	TextWhite = Color3.fromRGB(240, 240, 240),-- สีตัวอักษรหลัก
	TextGray = Color3.fromRGB(180, 180, 180), -- สีตัวอักษรของ
	Border = Color3.fromRGB(70, 70, 80)       -- สีขอบจางๆ
}

-- Helper function to create instances easily
local function create(class, props)
	local o = Instance.new(class)
	if props then
		for k,v in pairs(props) do
			if k == "Parent" then o.Parent = v else pcall(function() o[k] = v end) end
		end
	end
	return o
end

-- Helper function to make a frame draggable
local function makeDraggable(topBarFrame, targetFrame)
	local dragging
	local dragInput
	local dragStart
	local startPos

	local function update(input)
		local delta = input.Position - dragStart
		targetFrame.Position = UDim2.new(startPos.X.Scale, startPos.X.Offset + delta.X, startPos.Y.Scale, startPos.Y.Offset + delta.Y)
	end

	topBarFrame.InputBegan:Connect(function(input)
		if input.UserInputType == Enum.UserInputType.MouseButton1 or input.UserInputType == Enum.UserInputType.Touch then
			dragging = true
			dragStart = input.Position
			startPos = targetFrame.Position

			input.Changed:Connect(function()
				if input.UserInputState == Enum.UserInputState.End then
					dragging = false
				end
			end)
		end
	end)

	topBarFrame.InputChanged:Connect(function(input)
		if input.UserInputType == Enum.UserInputType.MouseMovement or input.UserInputType == Enum.UserInputType.Touch then
			dragInput = input
		end
	end)

	UserInputService.InputChanged:Connect(function(input)
		if input == dragInput and dragging then
			update(input)
		end
	end)
end


-- =================================================================
-- GUI Creation Structure
-- =================================================================
local parent = game:GetService("CoreGui")
local gui = create("ScreenGui", {Name = "ReuploaderPluginModernUI", Parent = parent, ResetOnSpawn = false, ZIndexBehavior = Enum.ZIndexBehavior.Sibling})

-- Main Frame Container
local mainGui = create("Frame", {
	Name = "MainFrame",
	Parent = gui, 
	Size = UDim2.new(0, 450, 0, 400), -- เพิ่มความสูงนิดหน่อย
	Position = UDim2.new(0.5, -225, 0.3, 0), 
	BackgroundColor3 = Theme.MainBg,
	BorderSizePixel = 0
})
create("UICorner", {Parent = mainGui, CornerRadius = UDim.new(0, 10)})
create("UIStroke", {Parent = mainGui, Color = Theme.Border, Thickness = 1, Transparency = 0.5})

-- [NEW] Draggable Title Bar
local titleBar = create("Frame", {
	Name = "TitleBar",
	Parent = mainGui,
	Size = UDim2.new(1, 0, 0, 40),
	BackgroundColor3 = Theme.TitleBg,
	BorderSizePixel = 0
})
create("UICorner", {Parent = titleBar, CornerRadius = UDim.new(0, 10)})
-- ซ่อน corner ด้านล่างเพื่อให้เนียนไปกับ main frame
local titleBarCover = create("Frame", {
	Parent = titleBar,
	Size = UDim2.new(1, 0, 0, 10),
	Position = UDim2.new(0, 0, 1, -10),
	BackgroundColor3 = Theme.TitleBg,
	BorderSizePixel = 0
})
local titleLabel = create("TextLabel", {
	Parent = titleBar, 
	Text = "  Asset Reuploader Tool", 
	Size = UDim2.new(1, 0, 1, 0), 
	BackgroundTransparency = 1, 
	TextColor3 = Theme.TextWhite, 
	Font = Enum.Font.SourceSansBold, 
	TextSize = 20,
	TextXAlignment = Enum.TextXAlignment.Left
})
create("UIPadding", {Parent = titleLabel, PaddingLeft = UDim.new(0,10)})

-- ทำให้ลากได้
makeDraggable(titleBar, mainGui)

-- Content Container (พื้นที่ใส่เนื้อหาด้านล่าง Title Bar)
local contentContainer = create("Frame", {
	Parent = mainGui,
	Size = UDim2.new(1, 0, 1, -40),
	Position = UDim2.new(0, 0, 0, 40),
	BackgroundTransparency = 1
})
create("UIPadding", {Parent = contentContainer, PaddingTop = UDim.new(0, 15), PaddingBottom = UDim.new(0, 15), PaddingLeft = UDim.new(0, 15), PaddingRight = UDim.new(0, 15)})
local contentLayout = create("UIListLayout", {Parent = contentContainer, SortOrder = Enum.SortOrder.LayoutOrder, Padding = UDim.new(0, 12)})


-- 1. Tab Buttons Container
local tabContainer = create("Frame", {
	Name = "TabContainer",
	Parent = contentContainer,
	Size = UDim2.new(1, 0, 0, 36),
	BackgroundTransparency = 1,
	LayoutOrder = 1
})
local tabLayout = create("UIListLayout", {Parent = tabContainer, FillDirection = Enum.FillDirection.Horizontal, SortOrder = Enum.SortOrder.LayoutOrder, Padding = UDim.new(0, 10)})

local function createTabBtn(text, active)
	local btn = create("TextButton", {
		Parent = tabContainer,
		Text = text,
		Size = UDim2.new(0.5, -5, 1, 0),
		BackgroundColor3 = active and Theme.AccentBlue or Theme.ContainerBg,
		TextColor3 = Theme.TextWhite,
		Font = Enum.Font.SourceSansBold,
		TextSize = 16,
		AutoButtonColor = true,
		BorderSizePixel = 0
	})
	create("UICorner", {Parent = btn, CornerRadius = UDim.new(0, 6)})
	return btn
end

local tabAnim = createTabBtn("Animation", true)
local tabSound = createTabBtn("Sound", false)
local currentTab = "Animation"

tabAnim.MouseButton1Click:Connect(function() 
	currentTab = "Animation" 
	tabAnim.BackgroundColor3 = Theme.AccentBlue
	tabSound.BackgroundColor3 = Theme.ContainerBg
end)
tabSound.MouseButton1Click:Connect(function() 
	currentTab = "Sound" 
	tabSound.BackgroundColor3 = Theme.AccentBlue
	tabAnim.BackgroundColor3 = Theme.ContainerBg
end)


-- 2. Port Input and Scan Button Group
local controlsGroup = create("Frame", {
	Parent = contentContainer,
	Size = UDim2.new(1, 0, 0, 38),
	BackgroundTransparency = 1,
	LayoutOrder = 2
})
create("UIListLayout", {Parent = controlsGroup, FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 10)})

local portBoxContainer = create("Frame", {
	Parent = controlsGroup,
	Size = UDim2.new(0.65, 0, 1, 0),
	BackgroundColor3 = Theme.ContainerBg,
	BorderSizePixel = 0
})
create("UICorner", {Parent = portBoxContainer, CornerRadius = UDim.new(0,6)})
local portBox = create("TextBox", {
	Parent = portBoxContainer, 
	PlaceholderText = "Port (e.g. 9229)", 
	Text = "",
	Size = UDim2.new(1, 0, 1, 0), 
	BackgroundTransparency = 1, 
	TextColor3 = Theme.TextWhite,
	PlaceholderColor3 = Theme.TextGray,
	Font = Enum.Font.SourceSans,
	TextSize = 16
})

local scanBtn = create("TextButton", {
	Parent = controlsGroup, 
	Text = "Scan Workspace", 
	Size = UDim2.new(0.35, -10, 1, 0), 
	BackgroundColor3 = Theme.AccentBlue,
	TextColor3 = Theme.TextWhite,
	Font = Enum.Font.SourceSansBold,
	TextSize = 16,
	BorderSizePixel = 0
})
create("UICorner", {Parent = scanBtn, CornerRadius = UDim.new(0,6)})


-- 3. Options (Checkbox)
local optionsGroup = create("Frame", {
	Parent = contentContainer,
	Size = UDim2.new(1, 0, 0, 30),
	BackgroundTransparency = 1,
	LayoutOrder = 3
})
-- ใช้ TextCheckBox แบบเดิม แต่จัดวางให้ดีขึ้น
local checkExistingBox = create("TextCheckBox", {
	Parent = optionsGroup,
	Text = "  ตรวจสอบของเก่าก่อน (ช้ากว่า แต่ปลอดภัย)",
	TextColor3 = Theme.TextWhite,
	Font = Enum.Font.SourceSans,
	TextSize = 15,
	Size = UDim2.new(1, 0, 1, 0),
	BackgroundTransparency = 1,
	Checked = false,
	BorderSizePixel = 0
})


-- 4. Start Button
local startBtn = create("TextButton", {
	Parent = contentContainer, 
	Text = "Start Reupload Process", 
	Size = UDim2.new(1, 0, 0, 42), -- ปุ่มใหญ่ขึ้น
	BackgroundColor3 = Theme.AccentGreen,
	TextColor3 = Theme.TextWhite,
	Font = Enum.Font.SourceSansBold,
	TextSize = 18,
	LayoutOrder = 4,
	BorderSizePixel = 0
})
create("UICorner", {Parent = startBtn, CornerRadius = UDim.new(0,8)})


-- 5. Status Label
local statusLabel = create("TextLabel", {
	Parent = contentContainer, 
	Text = "Status: Ready to scan.", 
	Size = UDim2.new(1, 0, 0, 20), 
	BackgroundTransparency = 1, 
	TextColor3 = Theme.TextGray,
	Font = Enum.Font.SourceSans,
	TextSize = 14,
	TextXAlignment = Enum.TextXAlignment.Left,
	LayoutOrder = 5
})


-- 6. List Scrolling Frame (Modern Look)
local listContainer = create("Frame", {
	Parent = contentContainer,
	Size = UDim2.new(1, 0, 1, -220), -- ใช้พื้นที่ที่เหลือ
	BackgroundColor3 = Theme.ContainerBg,
	BorderSizePixel = 0,
	LayoutOrder = 6
})
create("UICorner", {Parent = listContainer, CornerRadius = UDim.new(0,6)})
create("UIPadding", {Parent = listContainer, PaddingTop = UDim.new(0,5), PaddingBottom = UDim.new(0,5), PaddingLeft = UDim.new(0,5), PaddingRight = UDim.new(0,5)})

local listFrame = create("ScrollingFrame", {
	Parent = listContainer, 
	Size = UDim2.new(1, 0, 1, 0), 
	BackgroundTransparency = 1,
	BorderSizePixel = 0,
	ScrollBarThickness = 6,
	ScrollBarImageColor3 = Theme.Border,
	CanvasSize = UDim2.new(0,0,0,0), -- ออโต้
	AutomaticCanvasSize = Enum.AutomaticSize.Y
})
local uiList = create("UIListLayout", {Parent = listFrame, Padding = UDim.new(0,2)})


-- =================================================================
-- LOGIC (ส่วนการทำงาน - เหมือนเดิมแทบทั้งหมด)
-- =================================================================
local collected = {}

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
	statusLabel.TextColor3 = Theme.TextWhite

	-- Clear old list
	for _,c in ipairs(listFrame:GetChildren()) do
		if c:IsA("Frame") then c:Destroy() end -- ลบ Frame แทน TextLabel
	end
	
	-- Populate new list with prettier rows
	for i = 1, math.min(#collected, 50) do -- เพิ่ม preview เป็น 50
		local ent = collected[i]
		
		-- สร้าง Row Frame สำหรับแต่ละรายการ
		local row = create("Frame", {
			Parent = listFrame,
			Size = UDim2.new(1, -6, 0, 24),
			-- ทำสีสลับบรรทัด (Zebra striping)
			BackgroundColor3 = (i % 2 == 0) and Theme.ContainerBg or Theme.MainBg,
			BorderSizePixel = 0
		})
		create("UICorner", {Parent = row, CornerRadius = UDim.new(0,4)})
		create("UIListLayout", {Parent = row, FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0,10)})
		create("UIPadding", {Parent = row, PaddingLeft = UDim.new(0,8), PaddingRight = UDim.new(0,8)})

		-- Index
		create("TextLabel", {Parent = row, Text = tostring(i)..".", Size = UDim2.new(0, 30, 1, 0), BackgroundTransparency = 1, TextColor3 = Theme.TextGray, Font = Enum.Font.SourceSans, TextXAlignment = Enum.TextXAlignment.Left})
		-- Name (ตัดคำถ้ายาวเกิน)
		create("TextLabel", {Parent = row, Text = ent.name, Size = UDim2.new(0.5, 0, 1, 0), BackgroundTransparency = 1, TextColor3 = Theme.TextWhite, Font = Enum.Font.SourceSansBold, TextXAlignment = Enum.TextXAlignment.Left, TextTruncate = Enum.TextTruncate.AtEnd})
		-- ID
		create("TextLabel", {Parent = row, Text = "ID: "..tostring(ent.oldId), Size = UDim2.new(0.3, 0, 1, 0), BackgroundTransparency = 1, TextColor3 = Theme.TextGray, Font = Enum.Font.SourceSans, TextXAlignment = Enum.TextXAlignment.Right})
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
		statusLabel.Text = "Error contacting server. Check port."
		statusLabel.TextColor3 = Color3.fromRGB(255, 100, 100) -- สีแดง
		return nil, res
	end
	
	local decoded, decodeErr = pcall(HttpService.JSONDecode, HttpService, res)
	if not decoded then
		statusLabel.Text = "Error decoding response."
		return nil, decodeErr
	end
	
	return decoded, nil
end

local function applySingleResult(result)
	local oldId = result.oldId
	local newId = result.newId
	local status = result.status
	
	if status ~= "ok" or not newId then
		statusLabel.Text = string.format("Failed %d: %s", oldId, result.error or "?")
		statusLabel.TextColor3 = Color3.fromRGB(255, 100, 100)
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
			if foundInstance then break end
		end
	end
	
	statusLabel.TextColor3 = Theme.TextWhite
	if result.skipped then
		statusLabel.Text = string.format("✓ Skipped (Found existing): %s", foundInstance and foundInstance.Name or oldId)
	elseif foundInstance then
		statusLabel.Text = string.format("✓ Reuploaded: %s (%d -> %d)", foundInstance.Name, oldId, newId)
	else
		statusLabel.Text = string.format("✓ Completed %d -> %d (Instance gone?)", oldId, newId)
	end
end

startBtn.MouseButton1Click:Connect(function()
	local portStr = portBox.Text:match("(%d+)")
	local port = tonumber(portStr)
	if not port then
		statusLabel.Text = "Please enter a valid port number."
		statusLabel.TextColor3 = Color3.fromRGB(255, 100, 100)
		return
	end
	
	if #collected == 0 then
		statusLabel.Text = "No items found. Press 'Scan Workspace' first."
		statusLabel.TextColor3 = Color3.fromRGB(255, 255, 100) -- สีเหลือง
		return
	end

	local shouldCheckExisting = checkExistingBox.Checked

	startBtn.Text = "Running... Please Wait"
	startBtn.BackgroundColor3 = Theme.TextGray -- เปลี่ยนสีปุ่มให้ดูว่าทำงานอยู่
	startBtn.Enabled = false
	checkExistingBox.Enabled = false
	scanBtn.Enabled = false

	task.spawn(function()
		local successCount = 0
		local failCount = 0
		
		for i, item in ipairs(collected) do
			statusLabel.Text = string.format("[%d/%d] Processing: %s...", i, #collected, item.name)
			statusLabel.TextColor3 = Theme.TextWhite
			
			local result, err = sendSingleToServer(port, item, shouldCheckExisting)
			
			if not result then
				failCount = failCount + 1
				warn("Server error on item " .. item.oldId .. ": " .. tostring(err))
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
		
		statusLabel.Text = string.format("Done! ✅ Success: %d, ❌ Failed: %d", successCount, failCount)
		if failCount > 0 then
			statusLabel.TextColor3 = Color3.fromRGB(255, 255, 100)
		else
			statusLabel.TextColor3 = Theme.AccentGreen
		end
		
		startBtn.Text = "Start Reupload Process"
		startBtn.BackgroundColor3 = Theme.AccentGreen
		startBtn.Enabled = true
		checkExistingBox.Enabled = true
		scanBtn.Enabled = true
	end)
end)

print("[Reuploader Plugin] Modern UI Loaded.")
