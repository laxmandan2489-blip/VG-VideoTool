# v3.1 VG PROCEDURAL 3D TEMPLATES – Blender ke andar chalta hai (sirf bpy/mathutils).
# Asli 3D: geometry, PBR + emission materials, lights, particles (instanced), fog/volume, DOF, motion blur,
# keyframed camera moves (dolly/orbit/crane/reveal/fly-through/macro) – photo zoom NAHI.
#
#   blender -b --factory-startup --python blender_templates.py -- job.json
#   (ya bpy module: run_job(dict))
#
# job.json: {"out_dir","frames","fps","width","height","template","camera","palette":{"accent":[r,g,b],
#            "accent2":[..],"bg":[..]},"engine":"EEVEE|CYCLES","samples","particles","seed","text","motion_blur"}
import bpy, sys, math, json, random
from mathutils import Vector

TEMPLATES = ["space", "planet", "globe", "solar_system", "dna", "molecule", "cell", "underwater", "technology",
             "mystery", "history", "infographic", "energy", "abstract"]
CAMERAS = ["push_in", "pull_out", "orbit", "crane_up", "reveal", "fly_through", "tracking", "macro_reveal"]


# ------------------------------------------------------------------ basics
def _lin(c):
    """sRGB 0-255 -> linear 0-1"""
    out = []
    for v in c[:3]:
        v = v / 255.0
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _inp(node, *names):
    for n in names:
        if n in node.inputs:
            return node.inputs[n]
    return None


def mat(name, color, metal=0.0, rough=0.4, emit=None, strength=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Metallic"].default_value = metal
    bs.inputs["Roughness"].default_value = rough
    if emit is not None and strength > 0:
        i = _inp(bs, "Emission Color", "Emission")
        if i: i.default_value = (*emit, 1)
        i = _inp(bs, "Emission Strength")
        if i: i.default_value = strength
    if transmission:
        i = _inp(bs, "Transmission Weight", "Transmission")
        if i: i.default_value = transmission
    if alpha < 1:
        bs.inputs["Alpha"].default_value = alpha
        try: m.surface_render_method = "BLENDED"
        except Exception:
            try: m.blend_method = "BLEND"
            except Exception: pass
    m.diffuse_color = (*color, 1)
    return m


def emissive(name, color, strength=6.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def noise_mat(name, c1, c2, scale=4.0, bump=0.3, rough=0.6, c3=None):
    """Procedural surface: noise -> color ramp (land/ocean, rock, skin) + bump."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bs = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    try: nz.inputs["Detail"].default_value = 8.0
    except Exception: pass
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.48; cr.color_ramp.elements[0].color = (*c1, 1)
    cr.color_ramp.elements[1].position = 0.55; cr.color_ramp.elements[1].color = (*c2, 1)
    if c3:
        el = cr.color_ramp.elements.new(0.72); el.color = (*c3, 1)
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = rough
    try:
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump
        nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], bs.inputs["Normal"])
    except Exception:
        pass
    return m


def put(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o


def smooth(o):
    try:
        for p in o.data.polygons: p.use_smooth = True
    except Exception:
        pass
    return o


def sphere(r, loc, m, seg=48):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(8, seg // 2), radius=r, location=loc)
    return smooth(put(bpy.context.object, m))


def ico(r, loc, m, sub=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    return put(bpy.context.object, m)


def cyl(r, depth, loc, m, rot=(0, 0, 0), v=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=depth, location=loc, rotation=rot)
    return smooth(put(bpy.context.object, m))


def cube(size, loc, m, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc); o = bpy.context.object; o.scale = scale
    return put(o, m)


def torus(R, r, loc, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot,
                                     major_segments=96, minor_segments=12)
    return smooth(put(bpy.context.object, m))


def key(o, attr, frame, value):
    setattr(o, attr, value); o.keyframe_insert(attr, frame=frame)


def spin(o, frames, axis=2, turns=0.25):
    r = list(o.rotation_euler); key(o, "rotation_euler", 1, tuple(r))
    r[axis] += math.tau * turns; key(o, "rotation_euler", frames, tuple(r))


def linear(o):
    ad = o.animation_data
    if not ad or not ad.action: return
    try:
        for fc in ad.action.fcurves:
            for k in fc.keyframe_points: k.interpolation = "LINEAR"
    except Exception:
        pass


def area(name, loc, power, color, size, target=(0, 0, 0)):
    d = bpy.data.lights.new(name, "AREA"); d.energy = power; d.color = color; d.shape = "DISK"; d.size = size
    o = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()
    return o


def spot(name, loc, power, color, angle=0.5, target=(0, 0, 0)):
    d = bpy.data.lights.new(name, "SPOT"); d.energy = power; d.color = color; d.spot_size = angle; d.spot_blend = 0.6
    o = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()
    return o


def world(color, strength=1.0, stars=False, fog=0.0):
    w = bpy.context.scene.world or bpy.data.worlds.new("W"); bpy.context.scene.world = w
    w.use_nodes = True; nt = w.node_tree
    bg = nt.nodes.get("Background")
    bg.inputs["Color"].default_value = (*color, 1); bg.inputs["Strength"].default_value = strength
    if fog > 0 and bpy.context.scene.render.engine == "CYCLES":
        fog = 0.0      # Cycles CPU pe world-volume bahut dheema (laptop atak jaata) – sirf Eevee me fog
    if fog > 0:
        try:
            out = nt.nodes.get("World Output")
            vs = nt.nodes.new("ShaderNodeVolumePrincipled")
            vs.inputs["Density"].default_value = fog
            vs.inputs["Color"].default_value = (*color, 1)
            nt.links.new(vs.outputs[0], out.inputs["Volume"])
        except Exception:
            pass


def particles(n, box, m, rmin=0.008, rmax=0.03, drift=(0, 0, 0.4), frames=60, seed=1):
    """Instanced chhote kan (dust / stars / plankton) – har ek dheere tairta hai."""
    rnd = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
    proto = put(bpy.context.object, m); proto.hide_render = True; proto.hide_viewport = True
    objs = []
    for i in range(n):
        o = proto.copy(); o.data = proto.data; bpy.context.scene.collection.objects.link(o)
        o.hide_render = False; o.hide_viewport = False
        s = rnd.uniform(rmin, rmax); o.scale = (s, s, s)
        p = Vector((rnd.uniform(-box[0], box[0]), rnd.uniform(-box[1], box[1]), rnd.uniform(-box[2], box[2])))
        o.location = p; o.keyframe_insert("location", frame=1)
        o.location = p + Vector(drift) * rnd.uniform(0.4, 1.2); o.keyframe_insert("location", frame=frames)
        linear(o); objs.append(o)
    return objs


# ------------------------------------------------------------------ camera system
def camera(kind, frames, target=(0, 0, 0), dist=6.0, height=0.6, lens=40, shake=0.0, fstop=2.8, focus=None):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("Cam"); cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam); sc.camera = cam; cd.lens = lens; cd.clip_end = 500
    tgt = bpy.data.objects.new("CamTarget", None); sc.collection.objects.link(tgt); tgt.location = target
    con = cam.constraints.new("TRACK_TO"); con.target = tgt; con.track_axis = "TRACK_NEGATIVE_Z"; con.up_axis = "UP_Y"
    T = Vector(target)

    def at(f, pos):
        cam.location = T + Vector(pos); cam.keyframe_insert("location", frame=f)

    if kind == "pull_out":
        at(1, (0, -dist * 0.62, height * 0.6)); at(frames, (0, -dist * 1.05, height * 1.2))
    elif kind == "orbit":
        n = 6
        for k in range(n + 1):
            a = -math.pi / 2 + (k / n) * math.radians(70)
            at(1 + int((frames - 1) * k / n), (dist * math.cos(a), dist * math.sin(a), height))
    elif kind == "crane_up":
        at(1, (0.4, -dist, -0.2)); at(frames, (-0.2, -dist * 0.85, height * 2.6))
        key(tgt, "location", 1, tuple(T + Vector((0, 0, -0.3)))); key(tgt, "location", frames, tuple(T + Vector((0, 0, 0.4))))
    elif kind == "reveal":
        at(1, (-dist * 0.7, -dist * 0.55, height)); at(frames, (dist * 0.15, -dist * 0.85, height * 1.1))
    elif kind == "fly_through":
        at(1, (0.3, -dist * 1.6, height)); at(frames, (-0.2, -dist * 0.35, height * 0.5))
    elif kind == "tracking":
        at(1, (-dist * 0.5, -dist, height)); at(frames, (dist * 0.5, -dist, height))
        key(tgt, "location", 1, tuple(T + Vector((-0.6, 0, 0)))); key(tgt, "location", frames, tuple(T + Vector((0.6, 0, 0))))
    elif kind == "macro_reveal":
        at(1, (0.2, -dist * 0.62, height * 0.3)); at(frames, (0, -dist * 0.95, height))
        cd.lens = max(lens, 60)
    else:                                                    # push_in (default, mystery/hook)
        at(1, (0, -dist * 1.05, height)); at(frames, (0, -dist * 0.68, height * 0.8))
    # smooth ease (bezier) – random jhatka nahi
    try:
        for fc in cam.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = "BEZIER"; k.easing = "AUTO"
                k.handle_left_type = "AUTO_CLAMPED"; k.handle_right_type = "AUTO_CLAMPED"
            if shake > 0:
                md = fc.modifiers.new("NOISE"); md.strength = shake; md.scale = 18
    except Exception:
        pass
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    cd.dof.focus_object = focus or tgt
    return cam


# ------------------------------------------------------------------ templates
def t_space(J, F, P):
    world(_lin(P["bg"]) if P["bg"] else (0.0, 0.0, 0.004), 1.0)
    star = emissive("Star", (1, 1, 1), 18)
    particles(J["particles"], (14, 6, 8), star, 0.006, 0.022, (0, 0, 0), F, J["seed"])
    planet = sphere(1.35, (0.4, 1.5, 0), noise_mat("Rock", _lin((70, 52, 40)), _lin((150, 105, 70)), 3.5, 0.5,
                                                   c3=_lin((210, 170, 120))), 64)
    spin(planet, F, 2, 0.08)
    sphere(1.40, (0.4, 1.5, 0), mat("Atmo", _lin(P["accent"]), alpha=0.07, emit=_lin(P["accent"]), strength=0.25), 48)
    sphere(0.5, (-6, 9, 2.5), emissive("Sun", _lin((255, 220, 170)), 40), 32)
    area("Sun key", (-6, 4, 3), 2500, (1, .9, .75), 3, (0.4, 1.5, 0))
    area("Rim", (3, 6, 1), 900, _lin(P["accent"]), 3, (0.4, 1.5, 0))
    return (0.4, 1.5, 0), 6.5


def t_planet(J, F, P, earth=False):
    world((0, 0, 0.003), 1.0)
    particles(J["particles"], (14, 6, 8), emissive("Star", (1, 1, 1), 15), 0.006, 0.02, (0, 0, 0), F, J["seed"])
    if earth:
        m = noise_mat("Earth", _lin((10, 40, 110)), _lin((46, 120, 52)), 2.2, 0.25, rough=0.5, c3=_lin((160, 140, 100)))
        try:                                                   # zameen zyada dikhe (pehle zyada samudra tha)
            m.node_tree.nodes["Color Ramp"].color_ramp.elements[0].position = 0.42
            m.node_tree.nodes["Color Ramp"].color_ramp.elements[1].position = 0.47
        except Exception:
            pass
    else:
        m = noise_mat("Planet", _lin(P["accent2"]), _lin(P["accent"]), 3.0, 0.4)
    p = sphere(1.6, (0, 0, 0), m, 96); p.rotation_euler = (math.radians(23), 0, 0); spin(p, F, 2, 0.12)
    sphere(1.66, (0, 0, 0), mat("Atmo", _lin((90, 160, 255)), alpha=0.07, emit=_lin((90, 160, 255)), strength=0.3), 64)
    if earth:
        sphere(1.63, (0, 0, 0), mat("Clouds", (1, 1, 1), alpha=0.25, rough=0.9), 64)
    area("Sun", (-5, -3, 2), 3000, (1, .95, .85), 4)
    area("Rim", (4, 4, 1), 700, (0.3, 0.5, 1), 4)
    return (0, 0, 0), 6.0


def t_solar(J, F, P):
    world((0, 0, 0.003), 1.0)
    particles(J["particles"], (16, 8, 8), emissive("Star", (1, 1, 1), 14), 0.006, 0.02, (0, 0, 0), F, J["seed"])
    sphere(0.8, (0, 0, 0), emissive("Sun", _lin((255, 190, 90)), 25), 48)
    pt = bpy.data.lights.new("SunLight", "POINT"); pt.energy = 4000; pt.color = (1, .85, .6)
    o = bpy.data.objects.new("SunLight", pt); bpy.context.scene.collection.objects.link(o)
    cols = [(160, 160, 160), (220, 180, 120), (60, 120, 220), (200, 90, 50), (210, 170, 120)]
    ring = emissive("Orbit", _lin(P["accent"]), 1.2)
    for k, (R, r, c) in enumerate(zip((1.4, 2.0, 2.7, 3.4, 4.3), (0.08, 0.13, 0.15, 0.11, 0.3), cols)):
        torus(R, 0.006, (0, 0, 0), ring)
        piv = bpy.data.objects.new(f"piv{k}", None); bpy.context.scene.collection.objects.link(piv)
        pl = sphere(r, (R, 0, 0), noise_mat(f"P{k}", _lin(c), _lin(tuple(min(255, x + 40) for x in c)), 4, 0.3), 32)
        pl.parent = piv
        piv.rotation_euler = (0, 0, k * 1.3)
        key(piv, "rotation_euler", 1, (0, 0, k * 1.3)); key(piv, "rotation_euler", F, (0, 0, k * 1.3 + 2.4 / (k + 1)))
        linear(piv)
    return (0, 0, 0), 9.0


def t_dna(J, F, P):
    world(_lin(P["bg"]), 0.6)
    a = mat("BaseA", _lin(P["accent"]), 0.2, 0.25, _lin(P["accent"]), 1.5)
    b = mat("BaseB", _lin(P["accent2"]), 0.2, 0.25, _lin(P["accent2"]), 1.5)
    rung = mat("Rung", (0.8, 0.85, 0.9), 0.1, 0.3, (0.6, 0.8, 1), 0.6)
    root = bpy.data.objects.new("Helix", None); bpy.context.scene.collection.objects.link(root)
    n = 26
    for i in range(n):
        z = (i - n / 2) * 0.22; ang = i * 0.55
        p1 = Vector((math.cos(ang), math.sin(ang), z)) * 1.0; p1.z = z
        p2 = Vector((math.cos(ang + math.pi), math.sin(ang + math.pi), z)); p2.z = z
        s1 = sphere(0.13, tuple(p1), a, 16); s2 = sphere(0.13, tuple(p2), b, 16)
        mid = (p1 + p2) / 2; d = (p2 - p1)
        c = cyl(0.035, d.length, tuple(mid), rung, v=12)
        c.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
        for o in (s1, s2, c): o.parent = root
    root.rotation_euler = (0, math.radians(12), 0)              # khada helix (9:16 frame me poora), halka jhuka
    key(root, "rotation_euler", 1, (0, math.radians(12), 0)); key(root, "rotation_euler", F, (0, math.radians(12), math.radians(150)))
    linear(root)
    particles(J["particles"] // 2, (5, 3, 4), emissive("Glow", _lin(P["accent"]), 6), 0.01, 0.03, (0, 0, 0.5), F, J["seed"])
    area("Key", (3, -4, 3), 1500, (1, 1, 1), 4); area("Rim", (-3, 3, 2), 1200, _lin(P["accent"]), 3)
    return (0, 0, 0), 6.5


def t_molecule(J, F, P):
    world(_lin(P["bg"]), 0.5)
    rnd = random.Random(J["seed"])
    root = bpy.data.objects.new("Mol", None); bpy.context.scene.collection.objects.link(root)
    cols = [_lin(P["accent"]), (0.9, 0.9, 0.95), _lin(P["accent2"]), (0.1, 0.4, 0.9)]
    atoms = [Vector((0, 0, 0))]
    for i in range(9):
        base = rnd.choice(atoms)
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized() * 1.0
        atoms.append(base + d)
    bond = mat("Bond", (0.7, 0.7, 0.75), 0.3, 0.3)
    for i, p in enumerate(atoms):
        r = 0.32 if i % 3 == 0 else 0.22
        o = sphere(r, tuple(p), mat(f"A{i}", cols[i % len(cols)], 0.1, 0.2), 32); o.parent = root
    for i in range(1, len(atoms)):
        j = min(range(i), key=lambda k: (atoms[k] - atoms[i]).length)
        d = atoms[i] - atoms[j]; c = cyl(0.06, d.length, tuple((atoms[i] + atoms[j]) / 2), bond, v=12)
        c.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); c.parent = root
    spin(root, F, 2, 0.3); linear(root)
    area("Key", (3, -4, 3), 1400, (1, 1, 1), 4); area("Rim", (-3, 3, 2), 1100, _lin(P["accent"]), 3)
    return (0, 0, 0), 6.0


def t_cell(J, F, P):
    world(_lin((10, 20, 30)), 0.5, fog=0.02)
    sphere(1.6, (0, 0, 0), mat("Membrane", _lin((120, 200, 255)), 0, 0.2, _lin((80, 160, 255)), 0.4, alpha=0.25), 64)
    nuc = sphere(0.55, (0.2, 0.1, 0.1), noise_mat("Nucleus", _lin((120, 40, 140)), _lin((200, 90, 200)), 6, 0.6), 48)
    spin(nuc, F, 2, 0.1)
    org = mat("Org", _lin(P["accent2"]), 0, 0.4, _lin(P["accent2"]), 0.8)
    rnd = random.Random(J["seed"])
    for i in range(14):
        p = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))).normalized() * rnd.uniform(0.8, 1.3)
        o = sphere(rnd.uniform(0.07, 0.16), tuple(p), org, 16); o.scale = (1.6, 1, 1)
    area("Key", (3, -4, 3), 1300, (1, 1, 1), 4); area("Back", (0, 4, 1), 1500, _lin(P["accent"]), 4)
    return (0, 0, 0), 5.5


def t_underwater(J, F, P):
    world(_lin((2, 18, 40)), 0.6, fog=0.06)
    floor = cube(1, (0, 0, -2.2), noise_mat("Sand", _lin((20, 40, 60)), _lin((50, 80, 90)), 1.5, 0.6), (30, 30, 0.1))
    rnd = random.Random(J["seed"])
    glow = _lin(P["accent"]) if P["accent"] else (0.2, 1, 0.9)
    jm = mat("Jelly", glow, 0, 0.2, glow, 4.0, alpha=0.55)
    for k in range(3):
        x, z = rnd.uniform(-1.2, 1.2), rnd.uniform(-0.5, 0.8)
        rb = 0.45 - k * 0.1
        bell = sphere(rb, (x, k * 1.2, z), jm, 32); bell.scale = (1, 1, 0.7)
        try:                                                 # aadha gumbad (dome), neeche se khula
            import bmesh
            bm = bmesh.new(); bm.from_mesh(bell.data)
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.05 * rb], context="VERTS")
            bm.to_mesh(bell.data); bm.free()
        except Exception:
            pass
        for t in range(8):                                   # lehraati tentacles (curves)
            a = t / 8 * math.tau
            cu = bpy.data.curves.new(f"tent{k}{t}", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.008
            sp = cu.splines.new("NURBS"); sp.points.add(4)
            for q in range(5):
                sp.points[q].co = (0.7 * rb * math.cos(a) + 0.06 * math.sin(q * 1.7 + t), 0.7 * rb * math.sin(a),
                                   -q * 0.22, 1)
            sp.use_endpoint_u = True
            co = bpy.data.objects.new(f"tent{k}{t}", cu); bpy.context.scene.collection.objects.link(co)
            co.data.materials.append(jm); co.parent = bell
        key(bell, "location", 1, (x, k * 1.2, z)); key(bell, "location", F, (x, k * 1.2, z + 0.35))
    particles(J["particles"], (5, 5, 3), emissive("Plankton", glow, 5), 0.006, 0.02, (0, 0, 0.25), F, J["seed"])
    spot("God rays", (0.5, 0.5, 6), 6000, (0.6, 0.85, 1), 0.7, (0, 0, -2))
    area("Fill", (-3, -4, 0), 300, (0.2, 0.5, 0.9), 4)
    return (0, 0.6, 0), 6.0


def t_technology(J, F, P):
    world(_lin((4, 8, 16)), 0.4)
    grid_m = emissive("Grid", _lin(P["accent"]), 3)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=30, y_subdivisions=30, size=16, location=(0, 0, -1.2))
    g = put(bpy.context.object, grid_m)
    try:
        wm = g.modifiers.new("Wire", "WIREFRAME"); wm.thickness = 0.012
    except Exception:
        pass
    body = mat("Chip", (0.04, 0.05, 0.06), 0.6, 0.25)
    gold = mat("Gold", _lin((230, 170, 60)), 1.0, 0.25)
    core = mat("Core", _lin(P["accent"]), 0.2, 0.2, _lin(P["accent"]), 5)
    layers = [cube(1, (0, 0, 0), body, (1.4, 1.4, 0.08)), cube(1, (0, 0, 0), core, (0.6, 0.6, 0.06)),
              cube(1, (0, 0, 0), gold, (1.1, 1.1, 0.02)), cube(1, (0, 0, 0), body, (0.9, 0.9, 0.12))]
    for i, l in enumerate(layers):                           # EXPLODED VIEW – parten upar-neeche khulti hain
        key(l, "location", 1, (0, 0, -0.3 + i * 0.1)); key(l, "location", max(2, int(F * 0.75)), (0, 0, -0.9 + i * 0.6))
    for i in range(16):
        a = i / 16 * math.tau
        p = cube(1, (1.75 * math.cos(a), 1.75 * math.sin(a), -0.3), gold, (0.05, 0.05, 0.25))
    particles(J["particles"] // 2, (4, 4, 2), emissive("Data", _lin(P["accent"]), 8), 0.008, 0.02, (0, 0, 1.0), F, J["seed"])
    area("Key", (3, -4, 4), 1200, (1, 1, 1), 4); area("Rim", (-3, 3, 2), 1500, _lin(P["accent"]), 3)
    return (0, 0, 0), 6.5


def t_mystery(J, F, P):
    world(_lin((6, 6, 10)), 0.25, fog=0.04)
    cube(1, (0, 0, -1.2), mat("Floor", (0.02, 0.02, 0.025), 0.2, 0.35), (20, 20, 0.05))
    mono = cube(1, (0, 1.0, 0.4), mat("Monolith", (0.06, 0.06, 0.07), 0.8, 0.12), (0.6, 0.25, 1.6))
    area("Back glow", (0, 2.6, 0.6), 1800, _lin(P["accent"]), 2.5, (0, 1, 0.4))     # silhouette rim
    area("Edge", (-2.5, -1, 1.5), 400, (0.7, 0.75, 1), 1.5, (0, 1, 0.4))
    sphere(0.12, (0, 0.85, 0.55), emissive("Eye", _lin(P["accent"]), 30), 24)
    particles(J["particles"], (4, 4, 2), mat("Dust", (0.8, 0.8, 0.8), 0, 0.9, (1, 1, 1), 0.4), 0.004, 0.012,
              (0.2, 0, 0.3), F, J["seed"])
    spot("Hero spot", (0, 0.6, 5), 3500, (0.9, 0.9, 1), 0.45, (0, 1, 0))
    area("Rim", (0, 4, 1), 500, _lin(P["accent"]), 2, (0, 1, 0.4))
    return (0, 1.0, 0.3), 6.0


def t_history(J, F, P):
    world(_lin((40, 26, 18)), 0.7, fog=0.03)
    stone = noise_mat("Stone", _lin((120, 100, 80)), _lin((170, 150, 120)), 8, 0.8, rough=0.85)
    cube(1, (0, 0, -1.3), stone, (14, 14, 0.2))
    for k in range(3):
        cube(1, (0, 0.5 + k * 0.35, -1.1 + k * 0.18), stone, (4.5 - k * 0.6, 0.35, 0.18))
    for i, x in enumerate((-2.0, -1.0, 0.0, 1.0, 2.0)):
        h = 2.6 if i != 3 else 1.3                          # ek toota hua khamba
        cyl(0.22, h, (x, 1.6, -0.6 + h / 2 - 0.05), stone, v=20)
        cube(1, (x, 1.6, -0.6 + h), stone, (0.6, 0.6, 0.12)) if i != 3 else None
    cube(1, (0, 1.6, 2.05), stone, (5, 0.7, 0.25))
    particles(J["particles"], (5, 4, 2), mat("Dust", (1, .85, .6), 0, 0.9, (1, .8, .5), 0.6), 0.004, 0.012,
              (0.3, 0, 0.2), F, J["seed"])
    area("Sunset", (-5, -2, 2.5), 4000, (1, .62, .3), 5, (0, 1.6, 0.5))
    area("Sky", (3, -4, 4), 600, (.5, .6, 1), 6, (0, 1.6, 0.5))
    return (0, 1.4, 0.5), 7.0


def t_infographic(J, F, P):
    world(_lin(P["bg"]), 0.5)
    cube(1, (0, 0, -1.0), mat("Base", (0.03, 0.03, 0.04), 0.3, 0.3), (8, 8, 0.05))
    vals = [0.4, 0.7, 0.55, 1.0, 0.85]
    for i, v in enumerate(vals):
        m = mat(f"Bar{i}", _lin(P["accent"] if i == 3 else (90, 100, 120)), 0.2, 0.3,
                _lin(P["accent"]) if i == 3 else None, 1.5 if i == 3 else 0)
        b = cube(1, ((i - 2) * 0.6, 0, -1.0), m, (0.4, 0.4, 0.01))
        key(b, "scale", 1, (0.4, 0.4, 0.01)); key(b, "location", 1, ((i - 2) * 0.6, 0, -1.0))
        f2 = max(2, int(F * (0.45 + i * 0.06)))
        key(b, "scale", f2, (0.4, 0.4, v * 2.4)); key(b, "location", f2, ((i - 2) * 0.6, 0, -1.0 + v * 1.2))
    txt = (J.get("text") or "").strip()
    if txt:
        bpy.ops.object.text_add(location=(0, -0.2, 1.75)); t = bpy.context.object
        t.data.body = txt[:14]; t.data.align_x = "CENTER"; t.data.extrude = 0.06; t.data.size = 0.7
        t.data.bevel_depth = 0.01; t.rotation_euler = (math.radians(90), 0, 0)
        put(t, mat("Txt", _lin(P["accent"]), 0.3, 0.3, _lin(P["accent"]), 2))
        key(t, "scale", 1, (0.01, 0.01, 0.01)); key(t, "scale", max(2, int(F * 0.3)), (1, 1, 1))
    area("Key", (3, -4, 4), 1300, (1, 1, 1), 4); area("Rim", (-3, 3, 2), 1000, _lin(P["accent"]), 3)
    return (0, 0, 0.3), 6.5


def t_energy(J, F, P):
    world(_lin(P["bg"]), 0.3)
    r1 = torus(1.3, 0.05, (0, 0, 0), emissive("Ring", _lin(P["accent"]), 12), (math.radians(90), 0, 0))
    r2 = torus(0.9, 0.025, (0, 0, 0), emissive("Ring2", _lin(P["accent2"]), 10), (math.radians(90), 0, 0))
    spin(r1, F, 1, 0.25); spin(r2, F, 1, -0.4)
    core = sphere(0.35, (0, 0, 0), emissive("Core", (1, 1, 1), 15), 32)
    key(core, "scale", 1, (0.6, 0.6, 0.6)); key(core, "scale", F, (1.2, 1.2, 1.2))
    particles(J["particles"], (3, 3, 3), emissive("Spark", _lin(P["accent"]), 10), 0.006, 0.02, (0, 0, 0.6), F, J["seed"])
    cube(1, (0, 0, -1.8), mat("Floor", (0.02, 0.02, 0.03), 0.8, 0.1), (12, 12, 0.05))
    return (0, 0, 0), 6.0


def t_abstract(J, F, P):
    world(_lin(P["bg"]), 0.4)
    hero = ico(1.0, (0, 0, 0), mat("Hero", _lin(P["accent"]), 0.9, 0.2), 3)
    spin(hero, F, 2, 0.2)
    torus(1.6, 0.02, (0, 0, 0), emissive("Halo", _lin(P["accent2"]), 6), (math.radians(80), 0, 0))
    particles(J["particles"], (5, 4, 3), emissive("Spark", _lin(P["accent"]), 6), 0.006, 0.02, (0, 0, 0.4), F, J["seed"])
    cube(1, (0, 0, -1.4), mat("Floor", (0.02, 0.02, 0.03), 0.6, 0.15), (14, 14, 0.05))
    area("Key", (3, -4, 3), 1500, (1, .9, .8), 4); area("Rim", (-3, 3, 2), 1500, _lin(P["accent"]), 3)
    return (0, 0, 0), 6.0


def t_doc_stage(J, F, P):
    """v3.31 UNIVERSAL 3D DOCUMENTARY STAGE: puts ANY photo (person, history, business, AI visual)
    onto a real 3D framed studio plane with reflective dark floor, dramatic 3-point rim lighting,
    floating particles, and real 3D Blender camera orbit/dolly."""
    import os
    world(_lin(P["bg"]), 0.25)
    # Dark glossy reflective studio floor
    cube(1, (0, 0, -1.55), mat("StudioFloor", (0.015, 0.02, 0.03), metal=0.65, rough=0.14), (16, 16, 0.05))
    # Back accent halo ring behind the 3D frame
    halo = torus(1.75, 0.025, (0, 0.55, 0.15), emissive("StageHalo", _lin(P["accent"]), 8.0), (math.radians(90), 0, 0))
    spin(halo, F, 1, 0.12)

    img_p = str(J.get("image_path") or "")
    pw, ph = 2.0, 2.5
    if img_p and os.path.isfile(img_p):
        try:
            im = bpy.data.images.load(img_p)
            iw, ih = im.size[0], im.size[1]
            if iw > 0 and ih > 0:
                ar = iw / ih
                if ar >= 1.0:
                    pw = 2.6; ph = max(1.3, 2.6 / ar)
                else:
                    ph = 2.7; pw = max(1.4, 2.7 * ar)
            # Matte backing frame (cream/dark metallic documentary bevel)
            cube(1, (0, 0.05, 0.15), mat("FrameBack", (0.08, 0.09, 0.11), metal=0.7, rough=0.25), (pw + 0.14, 0.06, ph + 0.14))
            # Textured front image plane
            bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0.0, 0.15), rotation=(math.radians(90), 0, 0))
            pl = bpy.context.object
            pl.scale = (pw, ph, 1.0)
            m = bpy.data.materials.new("DocPhotoMat")
            m.use_nodes = True
            nt = m.node_tree
            bs = nt.nodes.get("Principled BSDF")
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = im
            nt.links.new(tex.outputs["Color"], bs.inputs["Base Color"])
            bs.inputs["Roughness"].default_value = 0.35
            bs.inputs["Metallic"].default_value = 0.05
            try:
                em_i = _inp(bs, "Emission Color", "Emission")
                if em_i: nt.links.new(tex.outputs["Color"], em_i)
                es_i = _inp(bs, "Emission Strength")
                if es_i: es_i.default_value = 0.22
            except Exception:
                pass
            put(pl, m)
        except Exception:
            cube(1, (0, 0, 0.15), mat("FallbackStage", _lin(P["accent"]), 0.7, 0.2), (2.0, 0.1, 2.4))
    else:
        cube(1, (0, 0, 0.15), mat("FallbackStage", _lin(P["accent"]), 0.7, 0.2), (2.0, 0.1, 2.4))

    # Floating cinematic dust motes + 3-point dramatic studio lighting
    particles(min(140, J["particles"]), (5, 4, 4), emissive("Dust", _lin(P["accent2"]), 5.0), 0.005, 0.016, (0, 0, 0.35), F, J["seed"])
    area("KeyLight", (2.8, -4.2, 2.6), 1400, (1.0, 0.96, 0.90), 3.2)
    area("RimLight", (-3.2, 2.8, 2.4), 1800, _lin(P["accent"]), 2.8)
    area("FillLight", (-2.6, -3.5, 0.8), 450, (0.75, 0.85, 1.0), 3.0)
    return (0, 0, 0.15), 5.0


BUILD = {"space": t_space, "planet": t_planet, "globe": lambda J, F, P: t_planet(J, F, P, True),
         "solar_system": t_solar, "dna": t_dna, "molecule": t_molecule, "cell": t_cell, "underwater": t_underwater,
         "technology": t_technology, "doc_stage": t_doc_stage, "mystery": t_mystery, "history": t_history,
         "infographic": t_infographic, "energy": t_energy, "abstract": t_abstract}
DEFAULT_CAM = {"space": "orbit", "planet": "push_in", "globe": "orbit", "solar_system": "crane_up", "dna": "orbit", "doc_stage": "orbit",
               "molecule": "macro_reveal", "cell": "macro_reveal", "underwater": "push_in", "technology": "orbit",
               "mystery": "push_in", "history": "crane_up", "infographic": "reveal", "energy": "push_in",
               "abstract": "orbit"}


def _engine(sc, want, samples):
    ids = {i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    if want == "CYCLES" and "CYCLES" in ids:
        sc.render.engine = "CYCLES"
        try:
            sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.device = "CPU"
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for t in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
                try:
                    prefs.compute_device_type = t; prefs.get_devices()
                    if any(d.type == t for d in prefs.devices):
                        for d in prefs.devices: d.use = True
                        sc.cycles.device = "GPU"; break
                except Exception:
                    continue
        except Exception:
            pass
        return "CYCLES/" + getattr(sc.cycles, "device", "CPU")
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if e in ids:
            sc.render.engine = e
            try: sc.eevee.taa_render_samples = samples
            except Exception: pass
            try: sc.eevee.use_volumetric_shadows = False; sc.eevee.volumetric_tile_size = "16"
            except Exception: pass
            return e
    sc.render.engine = "CYCLES"; return "CYCLES(fallback)"


def run_job(J):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    F = int(J["frames"]); P = J.get("palette") or {}
    P.setdefault("accent", [64, 220, 255]); P.setdefault("accent2", [255, 214, 10]); P.setdefault("bg", [6, 10, 24])
    J.setdefault("particles", 200); J.setdefault("seed", 7)
    tpl = J.get("template") if J.get("template") in BUILD else "abstract"
    sc.frame_start = 1; sc.frame_end = F; sc.render.fps = int(J.get("fps", 30))
    sc.render.resolution_x = int(J["width"]); sc.render.resolution_y = int(J["height"])
    sc.render.resolution_percentage = 100
    eng = _engine(sc, J.get("engine", "EEVEE").upper(), int(J.get("samples", 16)))
    try: sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try: sc.view_settings.view_transform = "Filmic"
        except Exception: pass
    if J.get("motion_blur"):
        try: sc.render.use_motion_blur = True
        except Exception: pass
    target, dist = BUILD[tpl](J, F, P)
    cam_kind = J.get("camera") if J.get("camera") in CAMERAS else DEFAULT_CAM.get(tpl, "push_in")
    camera(cam_kind, F, target, dist, 0.6, 38 if J["height"] > J["width"] else 45, float(J.get("shake", 0.0)))
    # v3.23 CINEMATIC COMPOSITOR: Fog Glow Bloom + Subtle Lens Chromatic Aberration + Color Grade
    try:
        sc.use_nodes = True
        nt = sc.node_tree
        nt.nodes.clear()
        rl = nt.nodes.new("CompositorNodeRLayers")
        gl = nt.nodes.new("CompositorNodeGlare")
        gl.glare_type = "FOG_GLOW"
        gl.quality = "HIGH"
        gl.threshold = 0.85
        gl.mix = 0.0
        gl.size = 7
        cb = nt.nodes.new("CompositorNodeColorBalance")
        cb.correction_method = "LIFT_GAMMA_GAIN"
        cb.lift = (0.97, 0.99, 1.03)   # cool cinematic shadows
        cb.gamma = (1.00, 1.00, 1.01)
        cb.gain = (1.04, 1.02, 0.98)   # warm highlights
        ld = nt.nodes.new("CompositorNodeLensdist")
        ld.inputs["Dispersion"].default_value = 0.004
        comp = nt.nodes.new("CompositorNodeComposite")
        nt.links.new(rl.outputs["Image"], gl.inputs["Image"])
        nt.links.new(gl.outputs["Image"], cb.inputs["Image"])
        nt.links.new(cb.outputs["Image"], ld.inputs["Image"])
        nt.links.new(ld.outputs["Image"], comp.inputs["Image"])
    except Exception:
        pass
    try:
        sc.eevee.use_gtao = True
        sc.eevee.use_bloom = True
        sc.eevee.bloom_intensity = 0.12
    except Exception:
        pass
    sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 95
    sc.render.filepath = str(J["out_dir"]).rstrip("/\\") + "/f_"
    print(f"VG_BLENDER template={tpl} camera={cam_kind} engine={eng} frames={F}", flush=True)
    bpy.ops.render.render(animation=True)
    print("VG_BLENDER_DONE", flush=True)
    return tpl, cam_kind, eng


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    run_job(json.loads(open(argv[0], encoding="utf-8").read()))
