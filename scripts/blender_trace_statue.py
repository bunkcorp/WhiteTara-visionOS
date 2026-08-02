"""
Fresh White Tara rig: statue-only → mesh volume trace → armature.

Assumes WhiteTara_Body already in the scene (normalized, Z-up, ~0.5m).
Run inside Blender (Scripting) or via Blender MCP.
"""
from __future__ import annotations

import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

OUT_JSON = Path("/Users/kevinwoods/Documents/White Tara/statue_trace.json")
BLEND_OUT = Path("/Users/kevinwoods/Documents/White Tara/White_Tara_Rig.blend")


def rob(pts, q=20):
    pts = np.asarray(pts, float)
    if len(pts) < 12:
        return pts.mean(0)
    lo, hi = np.percentile(pts, q, 0), np.percentile(pts, 100 - q, 0)
    keep = np.all((pts >= lo) & (pts <= hi), 1)
    return (pts[keep] if keep.sum() > 8 else pts).mean(0)


def V(a):
    a = np.asarray(a, float).ravel()
    return Vector((float(a[0]), float(a[1]), float(a[2])))


def clear_rig_and_traces():
    body = bpy.data.objects.get("WhiteTara_Body")
    if body is None:
        raise RuntimeError("WhiteTara_Body not found")
    if body.parent:
        mw = body.matrix_world.copy()
        body.parent = None
        body.matrix_world = mw
    for mod in list(body.modifiers):
        body.modifiers.remove(mod)
    body.vertex_groups.clear()

    keep = {"WhiteTara_Body", "Crystal_Crystal_0", "Jewels_Jewels_0"}
    for obj in list(bpy.data.objects):
        if obj.name in keep:
            continue
        if (
            obj.name.startswith("TRACE_")
            or obj.name.startswith("LM_")
            or obj.name.startswith("LABEL_")
            or obj.type == "ARMATURE"
            or obj.name in {"FingerMarkers", "Tara_Labels"}
        ):
            bpy.data.objects.remove(obj, do_unlink=True)
    return body


def trace_statue(body):
    coords = np.array(
        [body.matrix_world @ v.co for v in body.data.vertices], dtype=np.float64
    )
    cx = 0.0
    cy = float(np.median(coords[(coords[:, 2] > 0.15) & (coords[:, 2] < 0.35)][:, 1]))

    def region_center(mask, q=25):
        pts = coords[mask]
        if len(pts) < 20:
            return None
        return rob(pts, q)

    def torso_at(z, half_w=0.045):
        m = (
            (np.abs(coords[:, 2] - z) < 0.012)
            & (np.abs(coords[:, 0] - cx) < half_w)
            & (np.abs(coords[:, 1] - cy) < 0.05)
        )
        return region_center(m, 30)

    pelvis = torso_at(0.105, 0.05)
    navel = torso_at(0.165, 0.045)
    sternum = torso_at(0.245, 0.04)
    clav = torso_at(0.305, 0.035)

    face_m = (
        (coords[:, 2] > 0.36)
        & (coords[:, 2] < 0.40)
        & (np.abs(coords[:, 0] - cx) < 0.03)
        & (coords[:, 1] > cy)
        & (coords[:, 1] < cy + 0.07)
    )
    chin = region_center(face_m & (coords[:, 2] < 0.375), 25)
    skull = region_center(
        (coords[:, 2] > 0.405)
        & (coords[:, 2] < 0.435)
        & (np.abs(coords[:, 0] - cx) < 0.03)
        & (np.abs(coords[:, 1] - cy) < 0.05),
        25,
    )
    crown = np.array([skull[0], skull[1], float(coords[:, 2].max())])

    def shoulder(side):
        m = (
            (coords[:, 2] > 0.300)
            & (coords[:, 2] < 0.330)
            & (np.abs(coords[:, 1] - cy) < 0.055)
        )
        if side < 0:
            m &= (coords[:, 0] < cx - 0.02) & (coords[:, 0] > cx - 0.09)
        else:
            m &= (coords[:, 0] > cx + 0.02) & (coords[:, 0] < cx + 0.075)
            m &= ~((coords[:, 0] > 0.055) & (coords[:, 1] > cy + 0.03))
        return region_center(m, 25)

    sh_L, sh_R = shoulder(-1), shoulder(+1)

    def arm_center(z, side, x_extent):
        m = np.abs(coords[:, 2] - z) < 0.015
        if side < 0:
            m &= (coords[:, 0] < -0.04) & (coords[:, 0] > -x_extent)
        else:
            m &= (coords[:, 0] > 0.04) & (coords[:, 0] < x_extent)
        return region_center(m, 22)

    elbow_L = arm_center(0.22, -1, 0.13)
    wrist_L = arm_center(0.12, -1, 0.15)
    palm_L = region_center(
        (coords[:, 2] > 0.07)
        & (coords[:, 2] < 0.105)
        & (coords[:, 0] < -0.09)
        & (coords[:, 0] > -0.16),
        20,
    )
    elbow_R = arm_center(0.235, +1, 0.12)
    palm_R = region_center(
        (coords[:, 2] > 0.28)
        & (coords[:, 2] < 0.33)
        & (coords[:, 0] > 0.05)
        & (coords[:, 1] > cy + 0.015),
        22,
    )
    wrist_R = 0.4 * elbow_R + 0.6 * palm_R

    knee_L = region_center(
        (coords[:, 2] > 0.075)
        & (coords[:, 2] < 0.11)
        & (coords[:, 0] < -0.08)
        & (coords[:, 0] > -0.15)
        & (coords[:, 1] < cy + 0.02),
        22,
    )
    knee_R = region_center(
        (coords[:, 2] > 0.075)
        & (coords[:, 2] < 0.11)
        & (coords[:, 0] > 0.08)
        & (coords[:, 0] < 0.15)
        & (coords[:, 1] < cy + 0.02),
        22,
    )
    ankle_L = region_center(
        (coords[:, 2] > 0.035)
        & (coords[:, 2] < 0.065)
        & (coords[:, 0] < -0.05)
        & (coords[:, 0] > -0.12),
        22,
    )
    ankle_R = region_center(
        (coords[:, 2] > 0.035)
        & (coords[:, 2] < 0.065)
        & (coords[:, 0] > 0.05)
        & (coords[:, 0] < 0.12),
        22,
    )
    hip_L = pelvis + np.array([-0.028, 0.005, 0.0])
    hip_R = pelvis + np.array([0.028, 0.005, 0.0])
    lotus = region_center(coords[:, 2] < 0.035, 30)

    kd = KDTree(len(coords))
    for i, c in enumerate(coords):
        kd.insert(c, i)
    kd.balance()

    def tips_near(palm, radius, n=5):
        idxs = [i for (_, i, _) in kd.find_range(tuple(palm), radius)]
        pts = coords[idxs]
        if len(pts) < 30:
            return [palm + np.array([0.01 * (i - 2), 0.01, 0.0]) for i in range(n)]
        c = pts.mean(0)
        d = np.linalg.norm(pts - c, axis=1)
        tips = []
        for i in np.argsort(-d):
            p = pts[i]
            if any(np.linalg.norm(p - t) < 0.009 for t in tips):
                continue
            tips.append(p)
            if len(tips) >= n:
                break
        return tips

    tips_L = tips_near(palm_L, 0.03)
    tips_R = tips_near(palm_R, 0.025)

    trace = {
        "method": "volume_centroids_from_statue_mesh",
        "cx": cx,
        "cy": cy,
        "lotus": lotus.tolist(),
        "pelvis": pelvis.tolist(),
        "navel": navel.tolist(),
        "sternum": sternum.tolist(),
        "clav": clav.tolist(),
        "chin": chin.tolist(),
        "skull": skull.tolist(),
        "crown": crown.tolist(),
        "shoulder_L": sh_L.tolist(),
        "shoulder_R": sh_R.tolist(),
        "elbow_L": elbow_L.tolist(),
        "elbow_R": elbow_R.tolist(),
        "wrist_L": wrist_L.tolist(),
        "wrist_R": np.asarray(wrist_R, float).tolist(),
        "palm_L": palm_L.tolist(),
        "palm_R": palm_R.tolist(),
        "fingers_L": [np.asarray(t, float).tolist() for t in tips_L],
        "fingers_R": [np.asarray(t, float).tolist() for t in tips_R],
        "knee_L": knee_L.tolist(),
        "knee_R": knee_R.tolist(),
        "ankle_L": ankle_L.tolist(),
        "ankle_R": ankle_R.tolist(),
        "hip_L": hip_L.tolist(),
        "hip_R": hip_R.tolist(),
        "map": {
            "L": "varada lowered -X (screen-left)",
            "R": "utpala raised +X (screen-right)",
            "face": "+Y",
        },
    }
    return coords, trace


def build_outline(coords):
    left, right = [], []
    for z in np.linspace(0.02, 0.48, 36):
        band = coords[np.abs(coords[:, 2] - z) < 0.008]
        if len(band) < 25:
            continue
        left.append(band[band[:, 0].argmin()])
        right.append(band[band[:, 0].argmax()])
    pts = list(left) + list(reversed(right))
    curve = bpy.data.curves.new("TRACE_Outline", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.0012
    spline = curve.splines.new("POLY")
    spline.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        spline.points[i].co = (float(p[0]), float(p[1]), float(p[2]), 1.0)
    obj = bpy.data.objects.new("TRACE_Outline", curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.show_in_front = True
    return obj


def build_armature(trace):
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.active_object
    arm.name = "WhiteTara_Armature"
    arm.show_in_front = True
    arm.data.display_type = "OCTAHEDRAL"
    arm.data.show_names = True
    for b in list(arm.data.edit_bones):
        arm.data.edit_bones.remove(b)

    def bone(name, head, tail, parent=None, connect=False):
        b = arm.data.edit_bones.new(name)
        b.head, b.tail = V(head), V(tail)
        if (b.tail - b.head).length < 0.006:
            b.tail = b.head + Vector((0.0, 0.008, 0.0))
        if parent is not None:
            b.parent = parent
            b.use_connect = connect
        return b

    pelvis, navel, sternum, clav = (
        trace["pelvis"],
        trace["navel"],
        trace["sternum"],
        trace["clav"],
    )
    sh_L, sh_R = trace["shoulder_L"], trace["shoulder_R"]
    elbow_L, elbow_R = trace["elbow_L"], trace["elbow_R"]
    wrist_L, wrist_R = trace["wrist_L"], trace["wrist_R"]
    palm_L, palm_R = trace["palm_L"], trace["palm_R"]
    chin, skull, crown = trace["chin"], trace["skull"], trace["crown"]
    hip_L, hip_R = trace["hip_L"], trace["hip_R"]
    knee_L, knee_R = trace["knee_L"], trace["knee_R"]
    ankle_L, ankle_R = trace["ankle_L"], trace["ankle_R"]

    root = bone("root", [pelvis[0], pelvis[1], 0.01], pelvis)
    hips = bone("hips", pelvis, navel, root, True)
    spine = bone("spine", navel, sternum, hips, True)
    chest = bone("chest", sternum, clav, spine, True)
    neck = bone("neck", clav, chin, chest, True)
    head = bone("head", chin, skull, neck, True)
    bone("crown", skull, crown, head, False)
    shl = bone("shoulder.L", clav, sh_L, chest)
    shr = bone("shoulder.R", clav, sh_R, chest)
    ual = bone("upper_arm.L", sh_L, elbow_L, shl, True)
    uar = bone("upper_arm.R", sh_R, elbow_R, shr, True)
    fal = bone("forearm.L", elbow_L, wrist_L, ual, True)
    far = bone("forearm.R", elbow_R, wrist_R, uar, True)
    hL = bone("hand.L", wrist_L, palm_L, fal, True)
    hR = bone("hand.R", wrist_R, palm_R, far, True)
    for i, tip in enumerate(trace["fingers_L"]):
        bone(f"finger.L.{i}", palm_L, tip, hL)
    for i, tip in enumerate(trace["fingers_R"]):
        bone(f"finger.R.{i}", palm_R, tip, hR)
    thl = bone("thigh.L", hip_L, knee_L, hips)
    thr = bone("thigh.R", hip_R, knee_R, hips)
    bone("shin.L", knee_L, ankle_L, thl, True)
    bone("shin.R", knee_R, ankle_R, thr, True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def mark(name, co, size=0.012):
    bpy.ops.object.empty_add(type="SPHERE", location=V(co))
    e = bpy.context.active_object
    e.name = name
    e.show_name = True
    e.empty_display_size = size
    e.show_in_front = True
    return e


def main():
    body = clear_rig_and_traces()
    coords, trace = trace_statue(body)
    OUT_JSON.write_text(json.dumps(trace, indent=2))
    bpy.context.scene["tara_trace"] = json.dumps(trace)
    build_outline(coords)
    arm = build_armature(trace)
    for name, key in [
        ("TRACE_palm_L", "palm_L"),
        ("TRACE_palm_R", "palm_R"),
        ("TRACE_elbow_L", "elbow_L"),
        ("TRACE_elbow_R", "elbow_R"),
        ("TRACE_knee_L", "knee_L"),
        ("TRACE_knee_R", "knee_R"),
        ("TRACE_chin", "chin"),
        ("TRACE_lotus", "lotus"),
    ]:
        mark(name, trace[key])
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))
    print(f"[Trace] armature={arm.name} bones={len(arm.data.bones)}")
    print(f"[Trace] saved {OUT_JSON} and {BLEND_OUT}")


if __name__ == "__main__":
    main()
