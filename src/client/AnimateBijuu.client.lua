-- Anime chaque bijū présent dans Workspace.Bijuu (côté client).

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Animator = require(ReplicatedStorage:WaitForChild("Bijuu"):WaitForChild("BijuuAnimator"))

local folder = workspace:WaitForChild("Bijuu")

local function hook(model)
	if model:IsA("Model") then
		Animator.start(model)
	end
end

for _, model in ipairs(folder:GetChildren()) do
	hook(model)
end
folder.ChildAdded:Connect(hook)
