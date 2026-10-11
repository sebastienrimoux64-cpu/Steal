-- Construit les 9 bijū dans Workspace.Bijuu au lancement de la partie.
-- (ServerScriptService, avec les ModuleScripts dans ReplicatedStorage.Bijuu)

local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Builder = require(ReplicatedStorage:WaitForChild("Bijuu"):WaitForChild("BijuuBuilder"))

local folder = workspace:FindFirstChild("Bijuu")
if folder then
	folder:Destroy()
end
folder = Instance.new("Folder")
folder.Name = "Bijuu"
folder.Parent = workspace

Builder.buildAll(folder, CFrame.new(0, 0, 0))
