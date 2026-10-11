--[[
	BijuuBuilder (ModuleScript)

	Construit les 9 bijū (Shukaku -> Kurama) entièrement en Parts cubiques,
	avec un rig complet en Motor6D (tête, mâchoire, pattes, queues segmentées...).

	Repère de chaque modèle : face avant = -Z, haut = +Y, "R" = +X, "L" = -X.
	Chaque modèle a une pièce "Root" invisible (PrimaryPart) : déplacez le
	modèle avec model:PivotTo(...).

	Utilisation :
		local Builder = require(path.to.BijuuBuilder)
		local kurama = Builder.build("Kurama", CFrame.new(0, 0, 0), workspace)
		Builder.buildAll(workspace, CFrame.new(0, 0, 0))
]]

local Builder = {}

local V3 = Vector3.new
local CF = CFrame.new
local RGB = Color3.fromRGB

local WHITE = RGB(245, 243, 235)
local BLACK = RGB(22, 22, 26)
local CLAW = RGB(240, 235, 215)

--------------------------------------------------------------------------
-- Outils de construction
--------------------------------------------------------------------------

local function sides(fn)
	fn(-1, "L")
	fn(1, "R")
end

local function newCtx(spec, origin)
	local model = Instance.new("Model")
	model.Name = spec.name

	local scale = spec.scale or 1
	local ctx = { model = model, scale = scale }

	-- Crée une Part (non rigée). Tailles et offsets sont multipliés par l'échelle.
	function ctx.part(name, size, offset, color, material)
		local p = Instance.new("Part")
		p.Name = name
		p.Size = size * scale
		p.CFrame = origin * CF(offset * scale)
		p.Color = color
		p.Material = material or Enum.Material.SmoothPlastic
		p.Anchored = false
		p.CanCollide = false
		p.Massless = true
		p.Parent = model
		return p
	end

	-- Crée un Motor6D reliant parent -> child avec un pivot de rotation donné
	-- (position dans le repère du modèle, avant échelle).
	function ctx.rig(parent, child, pivot, jointName)
		local pv = origin * CF(pivot * scale)
		local m = Instance.new("Motor6D")
		m.Name = jointName or child.Name
		m.Part0 = parent
		m.Part1 = child
		m.C0 = parent.CFrame:ToObjectSpace(pv)
		m.C1 = child.CFrame:ToObjectSpace(pv)
		m.Parent = child
		return m
	end

	-- Part + Motor6D vers `parent` (pivot = centre de la part par défaut).
	function ctx.add(name, size, offset, color, material, parent, pivot)
		local p = ctx.part(name, size, offset, color, material)
		ctx.rig(parent, p, pivot or offset, name)
		return p
	end

	return ctx
end

--------------------------------------------------------------------------
-- Générateur de quadrupède / créature (tout est paramétré par `spec`)
--------------------------------------------------------------------------

local function buildTails(ctx, spec, g)
	local n = spec.tails or 0
	if n <= 0 then
		return
	end

	local B = spec.body
	local tw, segs = spec.tailW, spec.tailSegs
	local ls = spec.tailLen / segs
	local rise = (spec.tailRise or 0.7) * tw
	local spread = (spec.tailSpread or 0.4) * tw
	local wave = (spec.tailWave or 0) * tw
	local tipSegs = spec.tipSegs or 1
	local mid = (n + 1) / 2

	for i = 1, n do
		local t = i - mid
		local x0 = math.clamp(t * tw * 0.55, -B.X / 2 + tw / 2, B.X / 2 - tw / 2)
		local a = V3(x0, g.baseY, g.rearZ - 0.3) -- point d'attache du segment courant
		local parent = g.body

		for k = 1, segs do
			local w = tw * (0.6 + 0.5 * math.sin(math.pi * k / (segs + 1)))
			local dx = t * spread + math.sin(k * 1.1 + i) * wave
			local dy = rise + (mid - math.abs(t)) * 0.08 * tw
			local step = V3(dx, dy, ls)
			local isTip = k > segs - tipSegs
			local seg = ctx.add(
				"Tail" .. i .. "_" .. k,
				V3(w, w, ls * 1.3),
				a + step / 2,
				isTip and spec.colors.tip or spec.colors.tail,
				spec.tailMat,
				parent,
				a
			)
			if spec.tailTransparency then
				seg.Transparency = spec.tailTransparency
			end
			parent = seg
			a = a + step
		end
	end
end

local function buildLegs(ctx, spec, g)
	local legH, legW = spec.legH, spec.legW
	if legH <= 0 or spec.legs == false then
		return
	end

	local B = spec.body
	local c = spec.colors
	local uh, lh, ph = legH * 0.45, legH * 0.40, legH * 0.15
	local limbColor = c.limb or c.body
	local pawColor = c.paw or limbColor

	local rows = {
		{ "Front", g.frontZ + legW * 0.9 },
		{ "Back", g.rearZ - legW * 0.9 },
	}
	for _, row in ipairs(rows) do
		local rowName, z = row[1], row[2]
		sides(function(s, n)
			local x = s * (B.X / 2 - legW * 0.55)
			local tag = rowName .. "Leg" .. n

			local upper = ctx.add(
				tag .. "_Upper",
				V3(legW * 1.15, uh + 0.4, legW * 1.3),
				V3(x, legH - uh / 2 + 0.2, z),
				limbColor,
				spec.bodyMat,
				g.body,
				V3(x, legH, z)
			)
			local lower = ctx.add(
				tag .. "_Lower",
				V3(legW, lh, legW),
				V3(x, legH - uh - lh / 2, z),
				limbColor,
				spec.bodyMat,
				upper,
				V3(x, legH - uh, z)
			)
			local paw = ctx.add(
				tag .. "_Paw",
				V3(legW * 1.1, ph, legW * 1.5),
				V3(x, ph / 2, z - legW * 0.2),
				pawColor,
				spec.bodyMat,
				lower,
				V3(x, ph, z)
			)
			for i = 1, 3 do
				ctx.add(
					tag .. "_Claw" .. i,
					V3(legW * 0.2, ph * 0.5, legW * 0.28),
					V3(x + (i - 2) * legW * 0.32, ph * 0.3, z - legW * 0.2 - legW * 0.8),
					c.claw or CLAW,
					nil,
					paw
				)
			end
		end)
	end
end

local function buildQuad(spec, origin)
	local ctx = newCtx(spec, origin)
	local c = spec.colors
	local B, H = spec.body, spec.head
	local legH = spec.legH
	local bodyTop = legH + B.Y
	local frontZ, rearZ = -B.Z / 2, B.Z / 2

	local g = {
		B = B,
		H = H,
		legH = legH,
		bodyTop = bodyTop,
		frontZ = frontZ,
		rearZ = rearZ,
		baseY = legH + B.Y * (spec.tailBaseY or 0.6),
		ears = {},
	}

	-- Root invisible (PrimaryPart) + corps
	local root = ctx.part("Root", V3(1, 1, 1), V3(0, legH + B.Y / 2, 0), c.body)
	root.Transparency = 1
	root.CanQuery = false
	root.Anchored = spec.anchored ~= false
	ctx.model.PrimaryPart = root
	g.root = root

	local body = ctx.add("Body", B, V3(0, legH + B.Y / 2, 0), c.body, spec.bodyMat, root)
	g.body = body

	ctx.add(
		"Belly",
		V3(B.X * 1.02, B.Y * 0.35, B.Z * 0.92),
		V3(0, legH + B.Y * 0.175 - 0.03, 0),
		c.belly,
		spec.bodyMat,
		body
	)

	if spec.bands then
		local count = spec.bands.count
		for i = 1, count do
			local z = frontZ + B.Z * i / (count + 1)
			ctx.add(
				"Band" .. i,
				V3(B.X * 1.03, B.Y * 1.03, spec.bands.thick),
				V3(0, legH + B.Y / 2, z),
				spec.bands.color,
				nil,
				body
			)
		end
	end

	-- Cou + tête
	local neckPivot = V3(0, legH + B.Y * 0.65, frontZ)
	local neck = ctx.add(
		"Neck",
		V3(H.X * 0.8, B.Y * 0.7, H.Z * 0.5),
		V3(0, legH + B.Y * 0.65, frontZ - H.Z * 0.1),
		c.body,
		spec.bodyMat,
		body,
		neckPivot
	)
	g.neck = neck

	local headCY = legH + B.Y * 0.8 + H.Y * 0.3
	local headCZ = frontZ - H.Z * 0.4
	g.headCY, g.headCZ, g.headTop = headCY, headCZ, headCY + H.Y / 2

	local head = ctx.add("Head", H, V3(0, headCY, headCZ), c.body, spec.bodyMat, neck, neckPivot)
	g.head = head

	-- Museau, nez, mâchoire, crocs
	local snoutLen = spec.snout
	local snoutW, snoutH = H.X * 0.5, H.Y * 0.38
	local snoutY = headCY - H.Y * 0.18
	local snoutZ = headCZ - H.Z / 2 - snoutLen / 2 + 0.2
	g.snoutY, g.snoutZ = snoutY, snoutZ
	ctx.add("Snout", V3(snoutW, snoutH, snoutLen), V3(0, snoutY, snoutZ), c.snout or c.body, spec.bodyMat, head)
	ctx.add(
		"Nose",
		V3(H.X * 0.2, H.Y * 0.15, 0.5),
		V3(0, snoutY + snoutH / 2 - 0.1, snoutZ - snoutLen / 2 - 0.1),
		c.nose or BLACK,
		nil,
		head
	)

	local jawW, jawH, jawLen = H.X * 0.44, H.Y * 0.14, snoutLen * 0.9
	local jawY = snoutY - snoutH / 2 - jawH / 2 + 0.02
	local jawZ = snoutZ + 0.1
	local jaw = ctx.add(
		"Jaw",
		V3(jawW, jawH, jawLen),
		V3(0, jawY, jawZ),
		c.jaw or c.belly,
		spec.bodyMat,
		head,
		V3(0, jawY, jawZ + jawLen / 2)
	)
	g.jaw = jaw

	if spec.fangs ~= false then
		local fw, fl = H.X * 0.07, H.Y * 0.22
		sides(function(s, n)
			ctx.add(
				"UpperFang" .. n,
				V3(fw, fl, fw),
				V3(s * snoutW * 0.38, snoutY - snoutH / 2 - fl / 2 + 0.05, snoutZ - snoutLen / 2 + fw),
				WHITE,
				nil,
				head
			)
			ctx.add(
				"LowerFang" .. n,
				V3(fw, fl * 0.8, fw),
				V3(s * jawW * 0.38, jawY + jawH / 2 + fl * 0.4 - 0.05, jawZ - jawLen / 2 + fw),
				WHITE,
				nil,
				jaw
			)
		end)
	end

	-- Yeux
	local eyeY, eyeZ = headCY + H.Y * 0.12, headCZ - H.Z / 2
	g.eyeY, g.eyeZ = eyeY, eyeZ
	sides(function(s, n)
		ctx.add(
			"Eye" .. n,
			V3(H.X * 0.2, H.Y * 0.13, 0.3),
			V3(s * H.X * 0.3, eyeY, eyeZ - 0.05),
			c.eye,
			Enum.Material.Neon,
			head
		)
		ctx.add(
			"Pupil" .. n,
			V3(H.X * 0.05, H.Y * 0.14, 0.35),
			V3(s * H.X * 0.3, eyeY, eyeZ - 0.08),
			BLACK,
			nil,
			head
		)
		ctx.add(
			"Brow" .. n,
			V3(H.X * 0.26, H.Y * 0.06, 0.4),
			V3(s * H.X * 0.3, eyeY + H.Y * 0.11, eyeZ - 0.02),
			c.accent,
			nil,
			head
		)
	end)

	-- Oreilles
	local style = spec.earStyle or "fox"
	if style == "fox" or style == "cat" then
		local mul = style == "fox" and 0.55 or 0.33
		local eh = H.Y * mul * (spec.earScale or 1)
		local ew, ed = H.X * 0.2, H.X * 0.16
		sides(function(s, n)
			local ey = g.headTop + eh / 2 - 0.1
			local ex = s * H.X * 0.32
			local ez = headCZ + H.Z * 0.15
			g.ears[n] = ctx.add("Ear" .. n, V3(ew, eh, ed), V3(ex, ey, ez), c.body, spec.bodyMat, head, V3(ex, ey - eh / 2, ez))
			if c.earTip then
				ctx.add("EarTip" .. n, V3(ew * 1.04, eh * 0.3, ed * 1.04), V3(ex, ey + eh * 0.35, ez), c.earTip, nil, g.ears[n])
			end
		end)
	elseif style == "round" then
		sides(function(s, n)
			ctx.add(
				"Ear" .. n,
				V3(H.X * 0.2, H.X * 0.2, H.X * 0.12),
				V3(s * H.X * 0.42, g.headTop - 0.2, headCZ + H.Z * 0.1),
				c.body,
				spec.bodyMat,
				head
			)
		end)
	end

	buildLegs(ctx, spec, g)
	buildTails(ctx, spec, g)

	if spec.extras then
		spec.extras(ctx, g)
	end

	-- Prêt pour l'éditeur d'animations Roblox
	local controller = Instance.new("AnimationController")
	controller.Name = "AnimationController"
	local animator = Instance.new("Animator")
	animator.Parent = controller
	controller.Parent = ctx.model

	ctx.model:SetAttribute("Bijuu", spec.name)
	ctx.model:SetAttribute("Tails", spec.tails or 0)
	return ctx.model
end

--------------------------------------------------------------------------
-- Les 9 bijū
--------------------------------------------------------------------------

local SPECS = {}

-- 1 : Shukaku (tanuki de sable)
SPECS.Shukaku = {
	name = "Shukaku",
	order = 1,
	scale = 1,
	body = V3(12, 10, 16),
	legH = 4,
	legW = 3,
	head = V3(9, 8, 8),
	snout = 3,
	earStyle = "round",
	colors = {
		body = RGB(214, 186, 120),
		belly = RGB(240, 225, 180),
		accent = RGB(40, 60, 170),
		eye = RGB(255, 230, 60),
		tail = RGB(214, 186, 120),
		tip = RGB(230, 205, 140),
	},
	bands = { count = 5, color = RGB(40, 60, 170), thick = 0.8 },
	tails = 1,
	tailSegs = 5,
	tailW = 3.6,
	tailLen = 14,
	tailRise = 0.8,
	extras = function(ctx, g)
		local H, B = g.H, g.B
		sides(function(s, n)
			ctx.add(
				"EyeRing" .. n,
				V3(H.X * 0.3, H.Y * 0.22, 0.25),
				V3(s * H.X * 0.3, g.eyeY, g.eyeZ + 0.05),
				BLACK,
				nil,
				g.head
			)
		end)
		ctx.add("ForeheadMark", V3(H.X * 0.18, H.Y * 0.22, 0.3), V3(0, g.headTop - H.Y * 0.2, g.eyeZ), RGB(40, 60, 170), nil, g.head)
		for i = 1, 5 do
			ctx.add(
				"SandTuft" .. i,
				V3(2, 2.5, 2),
				V3(((i % 2) * 2 - 1) * 1.2, g.bodyTop + 1, g.frontZ + B.Z * i / 6),
				RGB(190, 160, 100),
				nil,
				g.body
			)
		end
	end,
}

-- 2 : Matatabi (chat à flammes bleues)
SPECS.Matatabi = {
	name = "Matatabi",
	order = 2,
	scale = 1,
	body = V3(8, 7, 13),
	legH = 5,
	legW = 2,
	head = V3(7, 6.5, 6),
	snout = 2,
	earStyle = "cat",
	colors = {
		body = RGB(150, 195, 240),
		belly = RGB(240, 248, 255),
		accent = RGB(30, 50, 140),
		eye = RGB(120, 255, 255),
		tail = RGB(150, 195, 240),
		tip = RGB(80, 190, 255),
		earTip = RGB(30, 50, 140),
		paw = RGB(30, 50, 140),
	},
	tails = 2,
	tailSegs = 6,
	tailW = 2.4,
	tailLen = 18,
	tailRise = 0.9,
	tailSpread = 0.8,
	tipSegs = 3,
	extras = function(ctx, g)
		local flame = Enum.Material.Neon
		local fc = RGB(80, 190, 255)
		for i = 1, 5 do
			ctx.add(
				"BackFlame" .. i,
				V3(1.2, 2.5 + (i % 2) * 1.2, 1.2),
				V3(0, g.bodyTop + 1, g.frontZ + g.B.Z * i / 6),
				fc,
				flame,
				g.body
			)
		end
		sides(function(s, n)
			ctx.add(
				"LegFlame" .. n,
				V3(1.4, 2, 1.4),
				V3(s * (g.B.X / 2 + 0.4), 3.2, g.rearZ - 1.8),
				fc,
				flame,
				g.body
			)
			ctx.add(
				"CheekFlame" .. n,
				V3(1.2, 2, 1.2),
				V3(s * (g.H.X / 2 + 0.6), g.headCY - 0.5, g.headCZ + 1),
				fc,
				flame,
				g.head
			)
		end)
	end,
}

-- 3 : Isobu (tortue à carapace piquante)
SPECS.Isobu = {
	name = "Isobu",
	order = 3,
	scale = 1,
	body = V3(13, 6, 14),
	legH = 3.5,
	legW = 3.5,
	head = V3(7, 6, 7),
	snout = 2,
	earStyle = "none",
	fangs = false,
	colors = {
		body = RGB(90, 120, 140),
		belly = RGB(225, 205, 160),
		accent = RGB(140, 70, 60),
		eye = RGB(255, 200, 70),
		tail = RGB(110, 140, 160),
		tip = RGB(210, 80, 70),
	},
	tails = 3,
	tailSegs = 4,
	tailW = 2.4,
	tailLen = 9,
	tailRise = 0.5,
	tailSpread = 0.7,
	tailBaseY = 0.45,
	extras = function(ctx, g)
		local B = g.B
		local shellC = RGB(140, 70, 60)
		local plate = ctx.add("Shell", V3(B.X * 0.95, 3, B.Z * 0.9), V3(0, g.bodyTop + 1.2, 0), shellC, nil, g.body)
		ctx.add("ShellRim", V3(B.X * 1.1, 1.4, B.Z * 1.05), V3(0, g.bodyTop + 0.2, 0), RGB(225, 205, 160), nil, plate)
		for ix = -1, 1 do
			for iz = -1, 1 do
				local x, z = ix * B.X * 0.28, iz * B.Z * 0.27
				local base = ctx.add(
					"ShellSpikeBase" .. ix .. iz,
					V3(2.6, 2.2, 2.6),
					V3(x, g.bodyTop + 3.7, z),
					RGB(105, 50, 45),
					nil,
					plate
				)
				ctx.add(
					"ShellSpikeTip" .. ix .. iz,
					V3(1.2, 2.4, 1.2),
					V3(x, g.bodyTop + 5.8, z),
					WHITE,
					nil,
					base
				)
			end
		end
		sides(function(s, n)
			ctx.add(
				"EyeSpike" .. n,
				V3(0.9, 1.6, 0.9),
				V3(s * g.H.X * 0.3, g.headTop + 0.6, g.headCZ - 1),
				WHITE,
				nil,
				g.head
			)
		end)
	end,
}

-- 4 : Son Goku (singe rouge à crinière)
SPECS.SonGoku = {
	name = "SonGoku",
	order = 4,
	scale = 1,
	body = V3(13, 12, 10),
	legH = 6,
	legW = 3.5,
	head = V3(8, 8, 8),
	snout = 3,
	earStyle = "round",
	colors = {
		body = RGB(200, 60, 55),
		belly = RGB(240, 230, 210),
		accent = RGB(245, 240, 230),
		eye = RGB(255, 220, 70),
		tail = RGB(200, 60, 55),
		tip = RGB(245, 240, 230),
		snout = RGB(235, 210, 185),
	},
	tails = 4,
	tailSegs = 5,
	tailW = 2.6,
	tailLen = 14,
	tailRise = 0.55,
	tailSpread = 0.6,
	extras = function(ctx, g)
		local white = RGB(245, 240, 230)
		for i = 1, 3 do
			ctx.add(
				"Mane" .. i,
				V3(g.H.X * (1.2 - i * 0.1), 3, 2.2),
				V3(0, g.headTop - i * 2.2, g.headCZ + g.H.Z / 2 + 0.6),
				white,
				nil,
				g.head
			)
		end
		sides(function(s, n)
			local hx = s * g.H.X * 0.3
			local h1 = ctx.add("Horn" .. n .. "_1", V3(1.4, 3, 1.4), V3(hx, g.headTop + 1.2, g.headCZ - 0.5), white, nil, g.head)
			local h2 = ctx.add("Horn" .. n .. "_2", V3(1.2, 2.5, 1.2), V3(s * g.H.X * 0.42, g.headTop + 3.6, g.headCZ - 0.5), white, nil, h1, V3(hx, g.headTop + 2.4, g.headCZ - 0.5))
			ctx.add("Horn" .. n .. "_3", V3(1, 2, 1), V3(s * g.H.X * 0.54, g.headTop + 5.4, g.headCZ - 0.5), white, nil, h2, V3(s * g.H.X * 0.42, g.headTop + 4.8, g.headCZ - 0.5))
			ctx.add(
				"ShoulderSpike" .. n,
				V3(2, 3, 2),
				V3(s * (g.B.X / 2 + 0.6), g.bodyTop - 0.5, g.frontZ + 2.5),
				white,
				nil,
				g.body
			)
			ctx.add(
				"ChestHair" .. n,
				V3(g.B.X * 0.3, 5, 0.8),
				V3(s * g.B.X * 0.18, g.legH + g.B.Y * 0.55, g.frontZ - 0.3),
				white,
				nil,
				g.body
			)
		end)
	end,
}

-- 5 : Kokuo (cheval-dauphin blanc à corne)
SPECS.Kokuo = {
	name = "Kokuo",
	order = 5,
	scale = 1,
	body = V3(8, 8, 16),
	legH = 7,
	legW = 2.4,
	head = V3(6, 7, 8),
	snout = 4,
	earStyle = "fox",
	earScale = 0.8,
	colors = {
		body = RGB(240, 240, 245),
		belly = RGB(255, 255, 255),
		accent = RGB(220, 60, 70),
		eye = RGB(255, 70, 70),
		tail = RGB(240, 240, 245),
		tip = RGB(220, 60, 70),
		paw = RGB(220, 60, 70),
		earTip = RGB(220, 60, 70),
		nose = RGB(220, 60, 70),
	},
	tails = 5,
	tailSegs = 5,
	tailW = 2,
	tailLen = 14,
	tailRise = 0.6,
	tailSpread = 0.7,
	tipSegs = 2,
	extras = function(ctx, g)
		local red = RGB(220, 60, 70)
		-- corne frontale en 3 blocs
		local h1 = ctx.add("Horn_1", V3(1.6, 2.4, 1.6), V3(0, g.headTop + 1, g.headCZ - 2), WHITE, nil, g.head)
		local h2 = ctx.add("Horn_2", V3(1.2, 2.4, 1.2), V3(0, g.headTop + 3.2, g.headCZ - 2.6), red, nil, h1, V3(0, g.headTop + 2.2, g.headCZ - 2))
		ctx.add("Horn_3", V3(0.8, 2.2, 0.8), V3(0, g.headTop + 5.2, g.headCZ - 3.2), WHITE, nil, h2, V3(0, g.headTop + 4.4, g.headCZ - 2.6))
		-- crinière rouge le long du cou et du dos
		for i = 1, 7 do
			ctx.add(
				"Mane" .. i,
				V3(1.4, 2 + (i % 2), 2),
				V3(0, g.bodyTop + 0.6 + (i == 1 and 2 or 0), g.frontZ + (i - 1) * 2.2),
				red,
				nil,
				g.body
			)
		end
		sides(function(s, n)
			ctx.add(
				"EyeMark" .. n,
				V3(g.H.X * 0.14, g.H.Y * 0.34, 0.25),
				V3(s * g.H.X * 0.3, g.eyeY - g.H.Y * 0.2, g.eyeZ + 0.05),
				red,
				nil,
				g.head
			)
			ctx.add(
				"Fin" .. n,
				V3(0.6, 3, 4),
				V3(s * (g.B.X / 2 + 0.3), g.legH + g.B.Y * 0.7, g.frontZ + 4),
				red,
				nil,
				g.body
			)
		end)
	end,
}

-- 6 : Saiken (limace géante à 6 queues)
SPECS.Saiken = {
	name = "Saiken",
	order = 6,
	scale = 1,
	body = V3(11, 9, 22),
	legH = 0,
	legW = 1,
	legs = false,
	head = V3(8, 7, 7),
	snout = 1.5,
	earStyle = "none",
	fangs = false,
	colors = {
		body = RGB(225, 235, 250),
		belly = RGB(185, 205, 235),
		accent = RGB(110, 160, 230),
		eye = RGB(255, 190, 60),
		tail = RGB(215, 230, 250),
		tip = RGB(150, 200, 255),
	},
	bands = { count = 6, color = RGB(190, 210, 240), thick = 0.9 },
	tails = 6,
	tailSegs = 6,
	tailW = 2.2,
	tailLen = 16,
	tailRise = 0.5,
	tailSpread = 0.5,
	tailWave = 0.4,
	tailTransparency = 0.2,
	tipSegs = 2,
	extras = function(ctx, g)
		ctx.add("Foot", V3(g.B.X * 1.12, 1.6, g.B.Z * 1.05), V3(0, 0.8, 0), RGB(185, 205, 235), nil, g.body)
		sides(function(s, n)
			local stalk = ctx.add(
				"Antenna" .. n,
				V3(0.9, 3.5, 0.9),
				V3(s * g.H.X * 0.28, g.headTop + 1.6, g.headCZ - 1),
				RGB(215, 230, 250),
				nil,
				g.head,
				V3(s * g.H.X * 0.28, g.headTop - 0.1, g.headCZ - 1)
			)
			ctx.add(
				"AntennaBall" .. n,
				V3(1.6, 1.6, 1.6),
				V3(s * g.H.X * 0.28, g.headTop + 3.8, g.headCZ - 1),
				RGB(110, 160, 230),
				Enum.Material.Neon,
				stalk
			)
		end)
		for i = 1, 5 do
			ctx.add(
				"BackBump" .. i,
				V3(2.4, 1.6, 2.4),
				V3(0, g.bodyTop + 0.6, g.frontZ + g.B.Z * i / 6),
				RGB(110, 160, 230),
				nil,
				g.body
			)
		end
	end,
}

-- 7 : Chomei (scarabée rhinocéros ailé)
SPECS.Chomei = {
	name = "Chomei",
	order = 7,
	scale = 1,
	body = V3(8, 7, 14),
	legH = 5,
	legW = 1.6,
	head = V3(7, 6, 6),
	snout = 1.5,
	earStyle = "none",
	colors = {
		body = RGB(60, 160, 90),
		belly = RGB(200, 210, 120),
		accent = RGB(30, 90, 60),
		eye = RGB(255, 60, 60),
		tail = RGB(170, 230, 190),
		tip = RGB(100, 200, 140),
		limb = RGB(40, 120, 70),
	},
	tails = 7,
	tailSegs = 3,
	tailW = 1.5,
	tailLen = 8,
	tailRise = 0.9,
	tailSpread = 0.8,
	tailTransparency = 0.2,
	tipSegs = 1,
	extras = function(ctx, g)
		local dark = RGB(30, 90, 60)
		-- corne de rhinocéros en 3 paliers
		local h1 = ctx.add("Horn_1", V3(1.6, 2, 1.6), V3(0, g.headTop + 0.6, g.headCZ - 1.5), dark, nil, g.head)
		local h2 = ctx.add("Horn_2", V3(1.3, 1.8, 1.8), V3(0, g.headTop + 2, g.headCZ - 3), dark, nil, h1, V3(0, g.headTop + 1.4, g.headCZ - 1.5))
		ctx.add("Horn_3", V3(1, 1.4, 2), V3(0, g.headTop + 2.8, g.headCZ - 4.8), dark, nil, h2, V3(0, g.headTop + 2.4, g.headCZ - 3))
		sides(function(s, n)
			-- élytres
			ctx.add(
				"Elytron" .. n,
				V3(g.B.X * 0.48, 1.2, g.B.Z * 0.8),
				V3(s * g.B.X * 0.25, g.bodyTop + 0.6, 0.5),
				dark,
				nil,
				g.body
			)
			-- ailes translucides
			local wing = ctx.add(
				"Wing" .. n,
				V3(8, 0.4, 16),
				V3(s * (g.B.X * 0.35 + 4), g.bodyTop + 1.4, 1),
				RGB(200, 245, 215),
				nil,
				g.body,
				V3(s * g.B.X * 0.3, g.bodyTop + 1.2, -2)
			)
			wing.Transparency = 0.4
			-- antennes
			ctx.add(
				"Antenna" .. n,
				V3(0.6, 3, 0.6),
				V3(s * g.H.X * 0.25, g.headTop + 1.2, g.headCZ - 2),
				dark,
				nil,
				g.head,
				V3(s * g.H.X * 0.25, g.headTop - 0.2, g.headCZ - 2)
			)
		end)
	end,
}

-- 8 : Gyūki (taureau-pieuvre à 8 tentacules)
SPECS.Gyuki = {
	name = "Gyuki",
	order = 8,
	scale = 1,
	body = V3(13, 11, 17),
	legH = 5,
	legW = 3.4,
	head = V3(9, 9, 9),
	snout = 3.5,
	earStyle = "cat",
	colors = {
		body = RGB(150, 70, 50),
		belly = RGB(230, 200, 170),
		accent = RGB(240, 235, 220),
		eye = RGB(255, 200, 60),
		tail = RGB(200, 140, 125),
		tip = RGB(235, 190, 170),
		snout = RGB(210, 160, 130),
	},
	tails = 8,
	tailSegs = 6,
	tailW = 2.6,
	tailLen = 20,
	tailRise = 0.25,
	tailSpread = 0.5,
	tailWave = 0.8,
	tailBaseY = 0.45,
	tipSegs = 1,
	extras = function(ctx, g)
		local horn = RGB(240, 235, 220)
		ctx.add("Hump", V3(g.B.X * 0.8, 3.5, 6), V3(0, g.bodyTop + 1.4, g.frontZ + 4), RGB(125, 55, 40), nil, g.body)
		sides(function(s, n)
			local hx = s * g.H.X * 0.5
			local h1 = ctx.add("Horn" .. n .. "_1", V3(1.8, 1.8, 1.8), V3(hx, g.headTop - 1.2, g.headCZ), horn, nil, g.head)
			local h2 = ctx.add("Horn" .. n .. "_2", V3(1.6, 1.6, 1.6), V3(s * (g.H.X * 0.5 + 1.8), g.headTop - 1.2, g.headCZ), horn, nil, h1, V3(hx, g.headTop - 1.2, g.headCZ))
			local h3 = ctx.add("Horn" .. n .. "_3", V3(1.4, 2.4, 1.4), V3(s * (g.H.X * 0.5 + 3.2), g.headTop + 0.4, g.headCZ), horn, nil, h2, V3(s * (g.H.X * 0.5 + 1.8), g.headTop - 1.2, g.headCZ))
			ctx.add("Horn" .. n .. "_4", V3(1.1, 2.2, 1.1), V3(s * (g.H.X * 0.5 + 3.6), g.headTop + 2.4, g.headCZ), horn, nil, h3, V3(s * (g.H.X * 0.5 + 3.2), g.headTop + 1.2, g.headCZ))
		end)
		ctx.add("NoseRing", V3(2.4, 0.5, 0.5), V3(0, g.snoutY - 1, g.snoutZ - 1.6), RGB(220, 190, 80), nil, g.head)
	end,
}

-- 9 : Kurama (renard à neuf queues)
SPECS.Kurama = {
	name = "Kurama",
	order = 9,
	scale = 1,
	body = V3(9, 8, 14),
	legH = 6,
	legW = 2.4,
	head = V3(7.5, 7, 7),
	snout = 3.5,
	earStyle = "fox",
	colors = {
		body = RGB(255, 140, 20),
		belly = RGB(255, 240, 215),
		accent = BLACK,
		eye = RGB(255, 20, 20),
		tail = RGB(255, 140, 20),
		tip = RGB(255, 235, 205),
		earTip = BLACK,
		paw = BLACK,
	},
	tails = 9,
	tailSegs = 6,
	tailW = 3,
	tailLen = 18,
	tailRise = 0.6,
	tailSpread = 0.45,
	tipSegs = 1,
	extras = function(ctx, g)
		local H = g.H
		sides(function(s, n)
			-- marques noires autour des yeux
			ctx.add(
				"EyeStreak" .. n,
				V3(H.X * 0.12, H.Y * 0.4, 0.25),
				V3(s * H.X * 0.3, g.eyeY - H.Y * 0.26, g.eyeZ + 0.05),
				BLACK,
				nil,
				g.head
			)
			-- touffes de poils sur les joues
			ctx.add(
				"CheekFur" .. n,
				V3(1.6, H.Y * 0.35, 2.4),
				V3(s * (H.X / 2 + 0.6), g.headCY - H.Y * 0.2, g.headCZ + 1),
				RGB(255, 140, 20),
				nil,
				g.head
			)
			-- moustaches
			for i = 1, 3 do
				ctx.add(
					"Whisker" .. n .. i,
					V3(2, 0.25, 0.25),
					V3(s * (H.X / 2 + 1.4), g.headCY - H.Y * 0.25 - (i - 2) * 0.6, g.headCZ - H.Z / 2 + 1.2),
					BLACK,
					nil,
					g.head
				)
			end
			-- marque noire sur l'épaule
			ctx.add(
				"ShoulderMark" .. n,
				V3(0.3, 2.4, 2.4),
				V3(s * (g.B.X / 2 + 0.05), g.bodyTop - 2.2, g.frontZ + 2.5),
				BLACK,
				nil,
				g.body
			)
		end)
		ctx.add("ForeheadMark", V3(1.2, 1.6, 0.3), V3(0, g.headTop - 1, g.eyeZ), BLACK, nil, g.head)
	end,
}

--------------------------------------------------------------------------
-- API publique
--------------------------------------------------------------------------

Builder.Specs = SPECS

-- Noms triés dans l'ordre 1 -> 9
Builder.Names = {}
for name in pairs(SPECS) do
	table.insert(Builder.Names, name)
end
table.sort(Builder.Names, function(a, b)
	return SPECS[a].order < SPECS[b].order
end)

function Builder.build(name, origin, parent)
	local spec = SPECS[name]
	assert(spec, "Bijuu inconnu : " .. tostring(name))
	local model = buildQuad(spec, origin or CFrame.new())
	model.Parent = parent or workspace
	return model
end

-- Construit les 9 bijū alignés sur l'axe X (spacing studs entre chaque).
function Builder.buildAll(parent, origin, spacing)
	origin = origin or CFrame.new()
	spacing = spacing or 55
	local models = {}
	for i, name in ipairs(Builder.Names) do
		local at = origin * CFrame.new((i - 5) * spacing, 0, 0)
		models[name] = Builder.build(name, at, parent)
	end
	return models
end

return Builder
