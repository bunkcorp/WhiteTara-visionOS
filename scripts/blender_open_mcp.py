"""Open White_Tara_Rig.blend and start BlenderMCP server."""
import addon_utils
import bpy
from pathlib import Path

BLEND = Path("/Users/kevinwoods/Documents/White Tara/White_Tara_Rig.blend")
ADDON = Path("/Users/kevinwoods/Desktop/white tara/blender-mcp/addon.py")


def ensure_mcp():
    try:
        bpy.ops.preferences.addon_install(filepath=str(ADDON), overwrite=True)
    except Exception:
        pass
    for mod in addon_utils.modules():
        name = mod.__name__
        if "mcp" in name.lower() or name == "addon":
            try:
                addon_utils.enable(name, default_set=True, persistent=True)
            except Exception:
                pass
    try:
        bpy.ops.blendermcp.start_server()
        print("[MCP] Server listening on localhost:9876")
    except Exception as e:
        print(f"[MCP] Click BlenderMCP → Connect in the N-panel. ({e})")


if BLEND.exists():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
ensure_mcp()
