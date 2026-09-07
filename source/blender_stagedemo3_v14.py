import bpy, math, bmesh
from mathutils import Vector
from pathlib import Path

ROOT=Path(r'C:/Users/ryuto/Documents/dev/game/Junction')
OUT=ROOT/'assets/models/stagedemo3_v14'
OUT.mkdir(parents=True,exist_ok=True)
sc=bpy.data.scenes.new('JUNCTION - The Connected Gallery')
bpy.context.window.scene=sc
sc.world=bpy.data.worlds.new('Gallery warm studio')
sc.world.color=(.15,.15,.15)
M={}; ASSETS={}
def E(p): return (p[0],-p[2],p[1])
def mat(name,color,metal=0):
    m=bpy.data.materials.new('V14_'+name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.62;bs.inputs['Metallic'].default_value=metal
    im=bpy.data.images.new('v14_'+name,width=32,height=32)
    pixels=[]
    for y in range(32):
        for x in range(32):
            f=1+.025*math.sin(x*4.71+y*2.89)+.018*math.sin(x*.36+y*.28)
            pixels.extend([min(1,c*f) for c in color]+[1])
    im.pixels=pixels;im.filepath_raw=str(OUT/('v14_'+name+'.png'));im.file_format='PNG';im.save()
    n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;m.node_tree.links.new(n.outputs['Color'],bs.inputs['Base Color'])
    M[name]=m
for n,c,k in [('stone',(.62,.55,.41),0),('chalk',(.88,.83,.69),0),('ink',(.075,.15,.16),0),('gold',(.95,.48,.10),.35),('copper',(.35,.15,.065),.4),('paper',(.24,.37,.34),0)]:mat(n,c,k)
PARTS=[]
def finish(o,name,material,bevel=0):
    o.name='V14_'+name;o.data.materials.append(M[material]);PARTS.append(o)
    if bevel:
        mod=o.modifiers.new('Crafted edges','BEVEL');mod.width=bevel;mod.segments=3
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def box(name,p,s,m='stone',b=.035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=E(p));o=bpy.context.object;o.scale=(s[0],s[2],s[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return finish(o,name,m,b)
def tube(name,points,r=.04,m='gold',cyclic=False):
    cv=bpy.data.curves.new(name,'CURVE');cv.dimensions='3D';cv.bevel_depth=r;cv.bevel_resolution=3;cv.resolution_u=1
    sp=cv.splines.new('POLY');sp.points.add(len(points)-1)
    for dst,p in zip(sp.points,points):dst.co=(*E(p),1)
    sp.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,cv);sc.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH')
    return finish(o,name,m)
def extrude(name,poly,depth,m='stone'):
    verts=[E((x,y,z)) for z in [-depth/2,depth/2] for x,y in poly];n=len(poly)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap');uv.active_render=True
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co.x*.15+.5,co.z*.15+.5)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bmesh.ops.triangulate(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);sc.collection.objects.link(o);bpy.context.view_layer.objects.active=o
    return finish(o,name,m,.025)
def export(name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in PARTS:o.select_set(True)
    bpy.context.view_layer.objects.active=PARTS[0];bpy.ops.object.join();o=bpy.context.object
    sc.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');o.name='V14_'+name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.gltf')),export_format='GLTF_SEPARATE',use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_texture_dir='textures')
    ASSETS[name]=o;PARTS.clear();print('EXPORTED',name,len(o.data.vertices),'vertices')

# Two complementary negative-space sculptures; aperture is a real empty volume.
for side,name in [(-1,'seam_left'),(1,'seam_right')]:
    arc=[(side*1.65*math.cos(t),2.5+1.65*math.sin(t)) for t in [i*math.pi/2/24 for i in range(25)]]
    poly=[(side*10,0),(side*1.65,0)]+arc+[(0,8),(side*10,8)]
    extrude(name,poly,.65,'chalk' if side<0 else 'ink')
    tube('Aperture seam',[(side*1.65,0,-.36)]+[(x,y,-.36) for x,y in arc],.055,'gold')
    for xx in range(3,10):box('Fluted face',(side*xx,4,-.36),(.026,7.5,.035),'copper',.008)
    export(name)

# Floor sighting glyph: two concentric broken rings plus a forward-facing notch.
for r in [.64,.85]:
    for a0 in [0,math.pi]:tube('Sight arc',[(r*math.cos(a0+t),.025,r*math.sin(a0+t)) for t in [i*math.pi*.85/36 for i in range(37)]],.025,'gold')
tube('Forward notch',[(-.15,.025,.48),(0,.025,.68),(.15,.025,.48)],.03,'gold')
export('sight_ring')

# Tactile paired-link handle, deliberately shared by all three chapters.
box('Plinth',(0,.5,0),(.85,1,.7),'ink',.1)
box('Crown',(0,1.02,0),(1.02,.16,.86),'chalk',.055)
for dx,zz in [(-.19,0),(.19,.10)]:
    tube('Link',[(dx+.30*math.cos(t),1.43+.36*math.sin(t),zz) for t in [i*2*math.pi/64 for i in range(64)]],.07,'gold',True)
export('connection_console')

# The frame has layered, stepped mouldings, corner keys and suspended depth lines.
for k in range(3):
    w=19+k*.35;h=8+k*.30;th=.12 if k!=1 else .24;z=k*.12
    for x in [-w/2,w/2]:box('Frame upright',(x,h/2-.45,z),(th,h,th),'gold' if k==1 else 'ink',.035)
    for y in [-.45,h-.45]:box('Frame lintel',(0,y,z),(w,th,th),'gold' if k==1 else 'ink',.035)
for x in [-9.5,9.5]:
    for y in [-.45,7.55]:box('Corner block',(x,y,-.1),(.45,.45,.35),'copper',.05)
export('painting_frame')

# Three separate sculpted ramps, with visible riser pattern and a brass walking edge.
for j in range(3):
    length=16/3;rise=3.2/3
    poly=[(0,-.35),(length,rise-.35),(length,rise),(0,0)]
    extrude('Painted ramp',poly,1.6,'chalk')
    for i in range(8):
        x=(i+.5)*length/8;y=x*rise/length
        box('Tread engraving',(x,y+.014,-.04),(.035,.025,1.55),'ink',.002)
    tube('Walkable edge',[(0,.045,-.81),(length,rise+.045,-.81)],.035,'gold')
    tube('Under spine',[(0,-.45,.25),(length,rise-.45,.25)],.11,'copper')
    export('painted_path_'+str(j))

# A human-sized paper-cut avatar, legible against the diorama from the fixed view.
body=[(-.32,.45),(-.23,1.24),(-.38,1.10),(-.48,.62),(-.61,.65),(-.47,1.42),(-.20,1.56),(.20,1.56),(.47,1.42),(.61,.65),(.48,.62),(.38,1.10),(.23,1.24),(.32,.45),(.22,.05),(.06,.05),(0,.65),(-.06,.05),(-.22,.05)]
extrude('Walker coat',body,.16,'gold')
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=.23,location=E((0,1.79,0)));finish(bpy.context.object,'Walker head','chalk')
export('paper_walker')

# A single authored staircase pivots about (0,7.2,72) in the engine.
for i in range(16):
    top=-4+.2*(i+1);zz=-8+i+.5
    box('Tread %02d'%i,(0,top-.10,zz),(4,.20,1.035),'chalk',.025)
    box('Brass nosing',(0,top+.006,zz-.48),(3.95,.025,.055),'gold',.008)
    for x in [-1.9,1.9]:
        tube('Baluster',[(x,top,zz),(x,top+1.0,zz)],.035,'copper')
for x in [-1.9,1.9]:
    tube('Handrail',[(x,-2.8,-7.5),(x,.2,7.5)],.065,'gold')
for x in [-1.25,1.25]:tube('Structural stringer',[(x,-4.3,-8),(x,-1.1,8)],.16,'ink')
export('inverted_stair')

# Vault ribs replace the former box-pillar corridor silhouette.
for side in [-1,1]:
    box('Pier',(side*10,4.5,0),(.45,9,.5),'ink',.075)
    tube('Vault',[(side*10*math.cos(t),9+3*math.sin(t),0) for t in [i*math.pi/2/40 for i in range(41)]],.23,'chalk')
    box('Foot',(side*10,.25,0),(.9,.5,.9),'chalk',.06)
export('vault_rib')

# Final sculpture: one unbroken trefoil knot as the reward for the three connections.
points=[]
for i in range(240):
    t=2*math.pi*i/240;r=1.0+.35*math.cos(3*t)
    points.append((r*math.cos(2*t),2.3+r*math.sin(2*t),.45*math.sin(3*t)))
tube('Continuous knot',points,.105,'gold',True)
box('Sculpture base',(0,.35,0),(2.3,.7,1.6),'ink',.12)
export('connected_knot')

# Arrange a labelled asset board in a new scene; the original Blender scene survives.
for i,(name,o) in enumerate(ASSETS.items()):
    o.location=E(((i%4)*24,0,(i//4)*20))
    bpy.ops.object.text_add(location=E(((i%4)*24-5,.05,(i//4)*20-5)))
    label=bpy.context.object;label.data.body=name;label.data.size=.7;label.data.materials.append(M['gold'])
sc.render.engine='CYCLES';sc.cycles.samples=24
bpy.ops.object.camera_add(location=(80,58,80));cam=bpy.context.object
direction=Vector((36,-19,2))-cam.location;cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=115;sc.camera=cam
for p,energy,size in [((25,15,55),42000,40),((65,-50,35),32000,30)]:
    bpy.ops.object.light_add(type='AREA',location=p);li=bpy.context.object;li.data.energy=energy;li.data.shape='DISK';li.data.size=size
    li.rotation_euler=(Vector((35,-20,0))-li.location).to_track_quat('-Z','Y').to_euler()
sc.render.resolution_x=1600;sc.render.resolution_y=1100;sc.render.resolution_percentage=100
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/stagedemo3_v14.blend'))
print('DONE: 12 authored glTF modules, Blender source saved; original scene preserved')
