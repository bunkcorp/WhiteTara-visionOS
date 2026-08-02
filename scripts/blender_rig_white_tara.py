"""
White Tara: normalize, build seated armature, auto-weight, idle clip, export USDZ.
Run: Blender --background --python this_file.py
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector, Euler

MODEL_PATH = Path(
    "/Users/kevinwoods/Documents/White Tara/Sources/White Tara/"
    "White Tara.rkassets/Models/White_Tara.usdz"
)
BLEND_OUT = Path("/Users/kevinwoods/Documents/White Tara/White_Tara_Rig.blend")
USDZ_OUT = Path(
    "/Users/kevinwoods/Documents/White Tara/Sources/White Tara/"
    "White Tara.rkassets/Models/White_Tara_Rigged.usdz"
)
TARGET_HEIGHT = 0.50


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def world_bounds(objs):
    min_c = Vector((float("inf"),) * 3)
    max_c = Vector((float("-inf"),) * 3)
    for obj in objs:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            min_c.x, min_c.y, min_c.z = min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)
            max_c.x, max_c.y, max_c.z = max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)
    return min_c, max_c


def import_model():
    before = set(bpy.data.objects)
    bpy.ops.wm.usd_import(filepath=str(MODEL_PATH))
    return [o for o in bpy.data.objects if o not in before]


def join_meshes(meshes):
    if not meshes:
        raise RuntimeError("No meshes to join")
    # Prefer body shells; keep jewels/crystal out of join if names allow (cleaner weights)
    body_parts = [m for m in meshes if "WhiteTara" in m.name or "whitetara" in m.name.lower()]
    if not body_parts:
        body_parts = meshes
    extras = [m for m in meshes if m not in body_parts]

    bpy.ops.object.select_all(action="DESELECT")
    for m in body_parts:
        m.select_set(True)
    bpy.context.view_layer.objects.active = body_parts[0]
    if len(body_parts) > 1:
        bpy.ops.object.join()
    body = bpy.context.active_object
    body.name = "WhiteTara_Body"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Clean overlapping Sketchfab shells for better heat weights
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    # Parent ornaments to body (move with whole figure even if unbound)
    for extra in extras:
        extra.parent = body
        print(f"[Rig] Parented ornament {extra.name} → body")
    return body


def normalize_body(body, target_height=TARGET_HEIGHT):
    bpy.context.view_layer.update()
    min_c, max_c = world_bounds([body])
    height = max_c.z - min_c.z
    if height < 1e-8:
        raise RuntimeError("Zero-height mesh")
    scale = target_height / height
    body.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    min_c, max_c = world_bounds([body])
    # Center X/Y, plant on Z=0
    cx = 0.5 * (min_c.x + max_c.x)
    cy = 0.5 * (min_c.y + max_c.y)
    body.location -= Vector((cx, cy, min_c.z))
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    min_c, max_c = world_bounds([body])
    print(f"[Rig] Normalized height={(max_c.z - min_c.z):.3f}m  bounds={min_c} → {max_c}")
    return min_c, max_c


def make_bone(arm, name, head, tail, parent=None):
    bone = arm.edit_bones.new(name)
    bone.head = Vector(head)
    bone.tail = Vector(tail)
    if parent is not None:
        bone.parent = parent
        bone.use_connect = False
    return bone


def build_seated_armature(min_c, max_c):
    """Simple deity armature sized to the mesh AABB (Blender Z-up)."""
    h = max_c.z - min_c.z
    w = max_c.x - min_c.x
    d = max_c.y - min_c.y
    cx = 0.5 * (min_c.x + max_c.x)
    cy = 0.5 * (min_c.y + max_c.y)

    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm_obj = bpy.context.active_object
    arm_obj.name = "WhiteTara_Armature"
    arm = arm_obj.data
    arm.name = "WhiteTara_ArmatureData"

    # Remove default bone
    for b in list(arm.edit_bones):
        arm.edit_bones.remove(b)

    # Approximate seated proportions
    hips_z = h * 0.22
    spine_z = h * 0.40
    chest_z = h * 0.55
    neck_z = h * 0.72
    head_z = h * 0.88
    crown_z = h * 0.98

    shoulder_x = w * 0.22
    shoulder_z = h * 0.58
    elbow_z = h * 0.42
    # Right hand in varada (near knee/front), left near heart/lotus
    hand_r = (cx + w * 0.28, cy + d * 0.15, h * 0.28)
    hand_l = (cx - w * 0.12, cy + d * 0.05, h * 0.48)

    root = make_bone(arm, "root", (cx, cy, 0.0), (cx, cy, hips_z * 0.5))
    hips = make_bone(arm, "hips", (cx, cy, hips_z * 0.5), (cx, cy, hips_z), root)
    spine = make_bone(arm, "spine", (cx, cy, hips_z), (cx, cy, spine_z), hips)
    chest = make_bone(arm, "chest", (cx, cy, spine_z), (cx, cy, chest_z), spine)
    neck = make_bone(arm, "neck", (cx, cy, chest_z), (cx, cy, neck_z), chest)
    head = make_bone(arm, "head", (cx, cy, neck_z), (cx, cy, crown_z), neck)

    # Shoulders / arms
    sh_l = make_bone(
        arm, "shoulder.L",
        (cx, cy, shoulder_z),
        (cx - shoulder_x, cy, shoulder_z),
        chest,
    )
    sh_r = make_bone(
        arm, "shoulder.R",
        (cx, cy, shoulder_z),
        (cx + shoulder_x, cy, shoulder_z),
        chest,
    )
    up_l = make_bone(
        arm, "upper_arm.L",
        (cx - shoulder_x, cy, shoulder_z),
        (cx - shoulder_x * 0.7, cy + d * 0.05, elbow_z),
        sh_l,
    )
    up_r = make_bone(
        arm, "upper_arm.R",
        (cx + shoulder_x, cy, shoulder_z),
        (cx + shoulder_x * 0.85, cy + d * 0.1, elbow_z),
        sh_r,
    )
    make_bone(arm, "forearm.L", up_l.tail, hand_l, up_l)
    make_bone(arm, "forearm.R", up_r.tail, hand_r, up_r)
    make_bone(arm, "hand.L", hand_l, (hand_l[0], hand_l[1] + 0.02, hand_l[2]), arm.edit_bones["forearm.L"])
    make_bone(arm, "hand.R", hand_r, (hand_r[0], hand_r[1] + 0.02, hand_r[2]), arm.edit_bones["forearm.R"])

    # Lotus legs (mostly for weight binding / subtle breath)
    make_bone(arm, "thigh.L", (cx, cy, hips_z), (cx - w * 0.28, cy + d * 0.15, h * 0.12), hips)
    make_bone(arm, "thigh.R", (cx, cy, hips_z), (cx + w * 0.28, cy + d * 0.15, h * 0.12), hips)
    make_bone(
        arm, "shin.L",
        arm.edit_bones["thigh.L"].tail,
        (cx - w * 0.1, cy + d * 0.22, h * 0.08),
        arm.edit_bones["thigh.L"],
    )
    make_bone(
        arm, "shin.R",
        arm.edit_bones["thigh.R"].tail,
        (cx + w * 0.1, cy + d * 0.22, h * 0.08),
        arm.edit_bones["thigh.R"],
    )

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def bind_body(body, arm_obj):
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        print("[Rig] Bound with automatic weights")
    except Exception as e:
        print(f"[Rig] AUTO weights failed ({e}); trying envelope")
        bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")


def create_idle_animation(arm_obj, frames=72):
    """Subtle breath + soft hand blessing motion (loopable)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pose = arm_obj.pose

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames

    def key_bone(name, frame, rot_euler=None, loc=None):
        pb = pose.bones.get(name)
        if pb is None:
            return
        pb.rotation_mode = "XYZ"
        if rot_euler is not None:
            pb.rotation_euler = Euler(rot_euler)
            pb.keyframe_insert(data_path="rotation_euler", frame=frame)
        if loc is not None:
            pb.location = loc
            pb.keyframe_insert(data_path="location", frame=frame)

    # Rest
    for name in pose.bones.keys():
        key_bone(name, 1, rot_euler=(0, 0, 0), loc=(0, 0, 0))
        key_bone(name, frames, rot_euler=(0, 0, 0), loc=(0, 0, 0))

    mid = frames // 2
    # Breath: chest/spine up slightly, head soft nod
    key_bone("spine", mid, rot_euler=(math.radians(-3), 0, 0), loc=(0, 0, 0.004))
    key_bone("chest", mid, rot_euler=(math.radians(-2), 0, 0), loc=(0, 0, 0.006))
    key_bone("head", mid, rot_euler=(math.radians(2), 0, math.radians(1)))
    # Right hand (varada) gentle give
    key_bone("forearm.R", mid, rot_euler=(math.radians(6), 0, math.radians(-4)))
    key_bone("hand.R", mid, rot_euler=(math.radians(8), 0, 0))
    # Left hand lotus stem micro-motion
    key_bone("forearm.L", mid, rot_euler=(math.radians(-4), math.radians(3), 0))
    key_bone("hand.L", mid, rot_euler=(0, math.radians(5), 0))

    # Blender 5 layered actions: use cyclic flag instead of FCurve modifiers
    if arm_obj.animation_data and arm_obj.animation_data.action:
        action = arm_obj.animation_data.action
        action.name = "WhiteTara_Idle"
        action.use_cyclic = True
        action.use_frame_range = True
        action.frame_start = 1
        action.frame_end = frames

    bpy.ops.object.mode_set(mode="OBJECT")
    print(f"[Rig] Created looping idle action ({frames} frames)")


def export_usdz(arm_obj, body):
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    body.select_set(True)
    # Include parented ornaments
    for child in body.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    USDZ_OUT.parent.mkdir(parents=True, exist_ok=True)

    kwargs = dict(
        filepath=str(USDZ_OUT),
        selected_objects_only=True,
        export_animation=True,
        export_materials=True,
    )
    try:
        bpy.ops.wm.usd_export(**kwargs)
    except TypeError:
        # Blender version differences in operator args
        bpy.ops.wm.usd_export(filepath=str(USDZ_OUT), selected_objects_only=True)
    print(f"[Rig] Exported {USDZ_OUT} ({USDZ_OUT.stat().st_size / 1e6:.1f} MB)")


def main():
    reset_scene()
    imported = import_model()
    meshes = [o for o in imported if o.type == "MESH"]
    # Drop empties/cameras leftover
    for o in list(imported):
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)

    body = join_meshes(meshes)
    min_c, max_c = normalize_body(body)
    arm_obj = build_seated_armature(min_c, max_c)
    bind_body(body, arm_obj)
    create_idle_animation(arm_obj)

    BLEND_OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))
    print(f"[Rig] Saved {BLEND_OUT}")

    try:
        export_usdz(arm_obj, body)
    except Exception as e:
        print(f"[Rig] USDZ export failed (open blend to export manually): {e}")


if __name__ == "__main__":
    main()
