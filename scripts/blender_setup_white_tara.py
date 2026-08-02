"""
Bootstrap White Tara rigging session:
1) Ensure BlenderMCP addon is loaded and listening
2) Import White_Tara.usdz
3) Normalize scale for altar work (~0.5 m tall)
"""
import addon_utils
import bpy
from mathutils import Vector
from pathlib import Path

ADDON_PATH = Path("/Users/kevinwoods/Desktop/white tara/blender-mcp/addon.py")
MODEL_PATH = Path(
    "/Users/kevinwoods/Documents/White Tara/Sources/White Tara/"
    "White Tara.rkassets/Models/White_Tara.usdz"
)
BLEND_OUT = Path("/Users/kevinwoods/Documents/White Tara/White_Tara_Rig.blend")


def ensure_mcp_addon():
    module_name = "addon"
    # Prefer installed blendermcp; fall back to loading local addon.py
    loaded = {m.__name__ for m in addon_utils.modules()}
    candidates = ["blende_mcp", "blendermcp", "addon", "BlenderMCP"]
    found = None
    for name in list(loaded):
        if "mcp" in name.lower() or name == "addon":
            found = name
            break

    if found is None and ADDON_PATH.exists():
        # Install from file into preferences
        bpy.ops.preferences.addon_install(filepath=str(ADDON_PATH), overwrite=True)
        # After install the module is usually named from filename: "addon"
        found = "addon"

    if found:
        try:
            addon_utils.enable(found, default_set=True, persistent=True)
            print(f"[WhiteTara] Enabled addon module: {found}")
        except Exception as e:
            print(f"[WhiteTara] Could not enable {found}: {e}")

    # Start MCP server operator if available
    try:
        bpy.ops.blendermcp.start_server()
        print("[WhiteTara] Started BlenderMCP server on port 9876")
    except Exception as e:
        print(f"[WhiteTara] Start server failed (click Connect in sidebar): {e}")


def clear_default_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for b in list(block):
            if b.users == 0:
                block.remove(b)


def import_white_tara():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(MODEL_PATH)

    before = set(bpy.data.objects)
    # Blender 4+/5 USD importer
    try:
        bpy.ops.wm.usd_import(filepath=str(MODEL_PATH))
    except Exception:
        # Fallback: some builds use this id
        bpy.ops.wm.usd_import(filepath=str(MODEL_PATH), import_materials=True)

    imported = [o for o in bpy.data.objects if o not in before]
    print(f"[WhiteTara] Imported {len(imported)} objects")
    return imported


def normalize_to_height(objects, target_height=0.5):
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        # Use all objects' bounds via parent
        meshes = list(objects)
    if not meshes:
        return

    # Compute world-space bounds
    min_c = Vector((float("inf"),) * 3)
    max_c = Vector((float("-inf"),) * 3)
    for obj in meshes:
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            min_c = Vector((min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)))
            max_c = Vector((max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)))

    height = max_c.z - min_c.z
    if height <= 1e-8:
        print("[WhiteTara] Height ~0, skip normalize")
        return

    scale = target_height / height
    print(f"[WhiteTara] Bounds height={height:.4f}m → scale={scale:.6f}")

    # Parent under empty for clean transform control
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    root = bpy.context.active_object
    root.name = "WhiteTara_Root"

    for obj in objects:
        obj.parent = root

    root.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    # Plant on Z=0 (Blender Z-up)
    min_c = Vector((float("inf"),) * 3)
    max_c = Vector((float("-inf"),) * 3)
    for obj in meshes:
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            min_c = Vector((min(min_c.x, w.x), min(min_c.y, w.y), min(min_c.z, w.z)))
            max_c = Vector((max(max_c.x, w.x), max(max_c.y, w.y), max(max_c.z, w.z)))
    root.location.z -= min_c.z
    bpy.context.view_layer.update()
    print(f"[WhiteTara] Planted on floor; final height≈{(max_c.z - min_c.z):.3f}m")


def main():
    ensure_mcp_addon()
    clear_default_scene()
    imported = import_white_tara()
    normalize_to_height(imported, target_height=0.5)
    BLEND_OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))
    print(f"[WhiteTara] Saved {BLEND_OUT}")
    print("[WhiteTara] Ready for armature. In Blender: sidebar → BlenderMCP → Connect to MCP server")


if __name__ == "__main__":
    main()
