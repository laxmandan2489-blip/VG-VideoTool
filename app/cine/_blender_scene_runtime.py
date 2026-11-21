# Executed by Blender; intentionally uses only bpy/mathutils (bundled in Blender).
import bpy, sys, math
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:]
out,dur,w,h,kind=args[0],float(args[1]),int(args[2]),int(args[3]),args[4]
sc=bpy.context.scene
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
# cinematic world
# Blender 4.x commonly exposes BLENDER_EEVEE_NEXT; newer/custom builds may
# expose BLENDER_EEVEE only. Select a registered engine instead of hard-coding.
_engine_items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
_engine_ids = {item.identifier for item in _engine_items}
if "BLENDER_EEVEE_NEXT" in _engine_ids:
 sc.render.engine="BLENDER_EEVEE_NEXT"
elif "BLENDER_EEVEE" in _engine_ids:
 sc.render.engine="BLENDER_EEVEE"
else:
 raise RuntimeError("No supported EEVEE render engine in this Blender build")
sc.render.resolution_x=w; sc.render.resolution_y=h; sc.render.resolution_percentage=100
sc.render.fps=24; sc.frame_start=1; sc.frame_end=max(24,int(dur*24))
sc.render.image_settings.file_format="FFMPEG"; sc.render.ffmpeg.format="MPEG4"; sc.render.ffmpeg.codec="H264"
sc.render.ffmpeg.constant_rate_factor="MEDIUM"; sc.render.ffmpeg.ffmpeg_preset="GOOD"
sc.world.color=(0.012,0.012,0.018)
def mat(name,color,metal=0,rough=.35):
 m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
 bs=m.node_tree.nodes.get("Principled BSDF"); bs.inputs["Base Color"].default_value=(*color,1); bs.inputs["Metallic"].default_value=metal; bs.inputs["Roughness"].default_value=rough
 return m
gold=mat("Burnished Gold",(0.62,.24,.035),.8,.22); dark=mat("Obsidian",(0.025,.03,.04),.35,.28); red=mat("Ember",(0.8,.045,.008),.15,.3)
def assign(o,m): o.data.materials.append(m); return o
# floor
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-1.4)); assign(bpy.context.object,dark)
# cinematic hero object by topic
if kind == "lion":
 # Stylized lion: muscular body, mane, muzzle, four legs and curved tail.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,radius=.85,location=(0,.05,-.15)); body=assign(bpy.context.object,gold); body.scale=(1.35,.58,.62)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=24,radius=.68,location=(.95,-.02,.35)); mane=assign(bpy.context.object,red); mane.scale=(.9,.8,1.0)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.34,location=(1.35,-.08,.3)); head=assign(bpy.context.object,gold); head.scale=(.8,.7,.72)
 for x in (1.52,1.18):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.13,location=(x,-.08,.62)); assign(bpy.context.object,gold)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.19,location=(1.62,-.18,.18)); assign(bpy.context.object,gold)
 for x in (-.72,.65):
  for y in (-.32,.32):
   bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=.16,depth=.7,location=(x,y,-.65)); leg=assign(bpy.context.object,gold); leg.rotation_euler[1]=-.12 if x>0 else .12
 bpy.ops.mesh.primitive_bezier_curve_add()
 tail=bpy.context.object; tail.data.dimensions="3D"; tail.data.bevel_depth=.055; tail.data.bevel_resolution=3
 tail.data.splines[0].bezier_points[0].co=(-1.05,0,-.1); tail.data.splines[0].bezier_points[1].co=(-1.55,0,.65)
 tail.data.splines[0].bezier_points[0].handle_right_type="AUTO"; tail.data.splines[0].bezier_points[1].handle_left_type="AUTO"; assign(tail,dark)
elif kind in ("animal","dinosaur"):
 # Generic four-legged animal / dinosaur silhouette (non-photoreal procedural asset).
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.72,location=(0,0,0)); body=assign(bpy.context.object,gold); body.scale=(1.35,.55,.65)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.35,location=(1.05,0,.35)); assign(bpy.context.object,gold)
 for x in (-.75,.65):
  for y in (-.32,.32):
   bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.12 if kind=="animal" else .18,depth=.7,location=(x,y,-.5)); assign(bpy.context.object,gold)
 if kind=="dinosaur":
  bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.28,radius2=.05,depth=.8,location=(.65,0,.65)); assign(bpy.context.object,gold)
elif kind in ("blackhole","galaxy","moon","volcano","rocket","atom"):
 if kind in ("blackhole","galaxy"):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=.8,location=(0,0,0)); assign(bpy.context.object,dark if kind=="blackhole" else red)
  for ang in (0,math.pi/3,2*math.pi/3):
   bpy.ops.mesh.primitive_torus_add(major_radius=1.15,minor_radius=.035,location=(0,0,0),rotation=(ang,.2,ang)); assign(bpy.context.object,gold)
 elif kind=="moon":
  bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=1.15,location=(0,0,0)); assign(bpy.context.object,dark)
 elif kind=="volcano":
  bpy.ops.mesh.primitive_cone_add(vertices=64,radius1=1.35,radius2=.25,depth=1.8,location=(0,0,-.35)); assign(bpy.context.object,dark)
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.3,location=(0,0,.5)); assign(bpy.context.object,red)
 elif kind=="rocket":
  bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.42,radius2=0,depth=1.7,location=(0,0,.2),rotation=(math.pi,0,0)); assign(bpy.context.object,gold)
  bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.28,radius2=0,depth=.8,location=(0,0,-.95)); assign(bpy.context.object,red)
 else:
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.28,location=(0,0,0)); assign(bpy.context.object,gold)
  for ang in (0,math.pi/3,2*math.pi/3):
   bpy.ops.mesh.primitive_torus_add(major_radius=.8,minor_radius=.025,location=(0,0,0),rotation=(ang,.4,0)); assign(bpy.context.object,red)
if kind in ("coin","gold"):
 bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1.25,depth=.22,location=(0,0,0))
 hero=assign(bpy.context.object,gold); hero.rotation_euler[0]=math.radians(75)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.45,location=(0,0,.18)); assign(bpy.context.object,gold)
elif kind in ("planet","earth","mars"):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,radius=1.3,location=(0,0,0)); hero=assign(bpy.context.object,red if kind=="mars" else gold)
 hero.rotation_euler[2]=0; hero.keyframe_insert("rotation_euler",frame=1); hero.rotation_euler[2]=math.tau; hero.keyframe_insert("rotation_euler",frame=sc.frame_end)
elif kind in ("fort","city"):
 # monumental architecture silhouette
 for x in (-1.4,-.7,0,.7,1.4):
  bpy.ops.mesh.primitive_cube_add(size=1,location=(x,0,.2)); o=assign(bpy.context.object,gold if x==0 else dark); o.scale=(.32,.5,1.2+(1.4-abs(x))*.35)
 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,1.5)); assign(bpy.context.object,gold)
elif kind in ("vehicle",):

 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0)); hero=assign(bpy.context.object,dark); hero.scale=(1.5,.55,.45)
 for x in (-1,.9):
  for y in (-.48,.48):
   bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.28,depth=.16,location=(x,y,-.45),rotation=(math.pi/2,0,0)); assign(bpy.context.object,red)
elif kind == "science":
 # atom-inspired orbital visual with animated electrons
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.35,location=(0,0,0)); assign(gold if False else bpy.context.object,gold)
 for ang in (0,math.pi/3,2*math.pi/3):
  bpy.ops.mesh.primitive_torus_add(major_radius=1.0,minor_radius=.025,location=(0,0,0),rotation=(ang,ang*.4,0)); assign(bpy.context.object,red)
elif kind == "weapon":
 bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,.4)); blade=assign(bpy.context.object,gold); blade.scale=(.12,.08,1.4)
 bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.22,depth=.12,location=(0,0,-.6)); assign(bpy.context.object,dark)
elif kind == "city":
 for i in range(9):
  h=.5+(i%4)*.45
  bpy.ops.mesh.primitive_cube_add(size=1,location=((i-4)*.48,.3,h/2-.8)); b=assign(bpy.context.object,dark); b.scale=(.38,.5,h)
elif kind in ("human","abstract"):
 # dramatic subject silhouette (not a rigged photoreal character)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.7,location=(0,0,.25)); body=assign(bpy.context.object,gold); body.scale=(.8,.45,1.15)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.42,location=(0,-.05,1.05)); assign(bpy.context.object,gold)
 for x in (-.38,.38):
  bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.13,depth=.8,location=(x,0,-.45)); assign(bpy.context.object,dark)
elif kind in ("nature","ocean","weather","city","fort"):
 # stylized cinematic terrain / wave-like forms
 for i in range(7):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.8,location=((i-3)*.65,.4,(i%3)*.35-.5)); o=assign(bpy.context.object,red if kind=="weather" else gold); o.scale=(1.1,.8,.65)
elif kind in ("fire",):
 for i in range(8):
  bpy.ops.mesh.primitive_cone_add(vertices=24,radius1=.3,radius2=0,depth=1.2,location=((i-4)*.25,0,.0)); assign(bpy.context.object,red)
else:
 # abstract cinematic hero prop, never default to a lion for unrelated narration
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1.0,location=(0,0,0)); hero=assign(bpy.context.object,gold); hero.keyframe_insert("rotation_euler",frame=1); hero.rotation_euler[2]=math.pi; hero.keyframe_insert("rotation_euler",frame=sc.frame_end)
# accent embers
for i in range(24):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=4,radius=.025,location=((i%8-4)*.45,-.25,(i//8)*.5-.4)); assign(bpy.context.object,red)
# lights
def area(name,loc,power,color,size):
 d=bpy.data.lights.new(name,"AREA"); d.energy=power; d.color=color; d.shape="DISK"; d.size=size
 o=bpy.data.objects.new(name,d); sc.collection.objects.link(o); o.location=loc; o.rotation_euler=(Vector((0,0,0))-o.location).to_track_quat("-Z","Y").to_euler()
area("Warm key",(3,-4,5),1500,(1,.48,.2),5); area("Rim",(0,3,3),2200,(.15,.35,1),4); area("Fill",(-4,-2,1),700,(1,.12,.04),3)
# camera
camd=bpy.data.cameras.new("Cinematic Camera"); cam=bpy.data.objects.new("Cinematic Camera",camd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(0,-6,1.2); cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat("-Z","Y").to_euler(); camd.lens=55; camd.dof.use_dof=True
# camera gentle push
cam.location=(0,-7,1.35); cam.keyframe_insert("location",frame=1); cam.location=(0,-5.8,1.1); cam.keyframe_insert("location",frame=sc.frame_end)
sc.render.image_settings.color_mode="RGB"; sc.view_settings.view_transform="AgX"
sc.render.filepath=out; sc.frame_set(1); bpy.ops.render.render(animation=True)
