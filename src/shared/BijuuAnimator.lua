--[[
	BijuuAnimator (ModuleScript)

	Anime un bijū construit par BijuuBuilder en modifiant `Motor6D.Transform`
	(respiration, balancement des queues, tête, mâchoire, marche, ailes).

	À lancer dans un LocalScript (l'animation est alors visible pour le joueur
	local ; Transform ne se réplique pas de façon fiable depuis le serveur).

	Attributs du modèle (booléens) pour piloter l'animation :
		Walking  -> cycle de marche des pattes
		Roar     -> bouche grande ouverte
		Flying   -> battement d'ailes rapide (Chomei)

	Pour des animations "pro", le modèle contient aussi un AnimationController
	+ Animator : utilisez l'éditeur d'animations Roblox (ou Moon Animator) sur
	ses Motor6D.
]]

local RunService = game:GetService("RunService")

local Animator = {}

function Animator.start(model)
	local motors = {}
	local tails = {}
	local legs = {}

	for _, d in ipairs(model:GetDescendants()) do
		if d:IsA("Motor6D") then
			motors[d.Name] = d
			local i, k = string.match(d.Name, "^Tail(%d+)_(%d+)$")
			if i then
				table.insert(tails, { m = d, i = tonumber(i), k = tonumber(k) })
			end
			local row, side, part = string.match(d.Name, "^(%a+)Leg([LR])_(%a+)$")
			if row and (part == "Upper" or part == "Lower") then
				table.insert(legs, { m = d, row = row, side = side, part = part })
			end
		end
	end

	local t0 = os.clock()
	local connection
	connection = RunService.Heartbeat:Connect(function()
		if not model.Parent then
			connection:Disconnect()
			return
		end

		local t = os.clock() - t0
		local walking = model:GetAttribute("Walking") == true
		local roaring = model:GetAttribute("Roar") == true
		local flying = model:GetAttribute("Flying") == true

		if motors.Body then
			motors.Body.Transform = CFrame.new(0, math.sin(t * 2) * 0.08, 0)
		end

		if motors.Head then
			motors.Head.Transform = CFrame.Angles(math.sin(t * 0.8) * 0.04, math.sin(t * 0.5) * 0.1, 0)
		end

		if motors.Jaw then
			local open = roaring and (0.55 + math.sin(t * 9) * 0.1) or (0.04 + math.sin(t * 2) * 0.02)
			motors.Jaw.Transform = CFrame.Angles(-open, 0, 0)
		end

		for _, e in ipairs(tails) do
			local sway = math.sin(t * 1.6 - e.k * 0.5 + e.i * 0.7) * (0.08 + 0.02 * e.k)
			local lift = math.sin(t * 1.2 - e.k * 0.4 + e.i) * 0.05
			e.m.Transform = CFrame.Angles(lift, sway, 0)
		end

		local phase = t * 6
		for _, l in ipairs(legs) do
			-- diagonales : avant-droite + arrière-gauche en phase
			local diag = ((l.row == "Front") == (l.side == "R")) and 0 or math.pi
			local swing = walking and math.sin(phase + diag) or 0
			if l.part == "Upper" then
				l.m.Transform = CFrame.Angles(swing * 0.5, 0, 0)
			else
				l.m.Transform = CFrame.Angles(walking and math.max(0, -math.cos(phase + diag)) * 0.5 or 0, 0, 0)
			end
		end

		local flap = flying and math.sin(t * 28) * 0.6 or math.sin(t * 3) * 0.04
		if motors.WingR then
			motors.WingR.Transform = CFrame.Angles(0, 0, flap)
		end
		if motors.WingL then
			motors.WingL.Transform = CFrame.Angles(0, 0, -flap)
		end
	end)

	return connection
end

return Animator
