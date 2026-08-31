import numpy as np
from pathlib import Path
import mathutils

SOMA30_NAMES = ["Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "Jaw", "LeftEye", "RightEye", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "LeftHandThumbEnd", "LeftHandMiddleEnd", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "RightHandThumbEnd", "RightHandMiddleEnd", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot", "RightToeBase"]
SOMA30_PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 6, 6, 3, 10, 11, 12, 13, 13, 3, 16, 17, 18, 19, 19, 0, 22, 23, 24, 0, 26, 27, 28]
SOMA30_OFFSETS = [[0, 0, 0], [-.00013727, .0500376256, -.00053726669], [-1.86574103e-9, .0712530139, -.000298248546], [-5.75188398e-9, .0755006305, -.00815970992], [-.00181676517, .263112953, -.00553348292], [-2.85102231e-8, .0770939664, .0230258546], [-4.5975437e-8, .0612891595, .0195370861], [2.63687901e-5, .0047559225, .0309494062], [.0320638079, .0538020513, .0758688308], [-.0322244017, .05361869, .0755823359], [.0162165175, .232371641, .0511341324], [.149198457, 2.19397873e-8, -.0550232576], [.287393078, 2.50268389e-9, -2.58787737e-5], [.270939812, -7.06625108e-9, 2.60897248e-5], [.122686267, -.0322017573, .0483306876], [.190119595, -.00312878387, -.000339570373], [-.0138011824, .231803086, .0521415786], [-.150371962, 1.17387901e-7, -.0554560437], [-.287366393, 1.87628082e-8, -2.59709359e-5], [-.271336198, -1.16767401e-9, 2.61269368e-5], [-.122642483, -.0321145448, .0480403904], [-.190005945, -.00306615542, -.0003157343], [.10043214, -.0843452671, .0259565473], [-1e-8, -.432217537, -.00802912805], [1e-8, -.421550959, -.0348152298], [0, -.0505947206, .132315294], [-.10047278, -.0829525995, .0262031695], [1e-8, -.433622059, -.00805555828], [2e-8, -.421173943, -.0347839785], [-3.42907669e-9, -.0507960932, .132841956]]

def export_bvh(item_dir: Path, output_bvh: Path):
    rot_data = np.fromfile(item_dir / "local_rotations_xyzw.f32", dtype=np.float32)
    root_data = np.fromfile(item_dir / "root_positions.f32", dtype=np.float32)
    
    num_frames = len(root_data) // 3
    rot_data = rot_data.reshape((num_frames, len(SOMA30_NAMES), 4))
    root_data = root_data.reshape((num_frames, 3))
    
    children_map = {}
    for i, p in enumerate(SOMA30_PARENTS):
        children_map.setdefault(p, []).append(i)
        
    lines = ["HIERARCHY"]
    
    def write_node(j: int, indent: int):
        pad = "  " * indent
        name = SOMA30_NAMES[j]
        off = SOMA30_OFFSETS[j]
        if j == 0:
            lines.append(f"{pad}ROOT {name}")
        else:
            lines.append(f"{pad}JOINT {name}")
        lines.append(f"{pad}{{")
        # Scale to cm (BVH standard: * 100)
        lines.append(f"{pad}  OFFSET {off[0]*100:.6f} {off[1]*100:.6f} {off[2]*100:.6f}")
        if j == 0:
            lines.append(f"{pad}  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation")
        else:
            lines.append(f"{pad}  CHANNELS 3 Zrotation Xrotation Yrotation")
            
        kids = children_map.get(j, [])
        if kids:
            for k in kids:
                write_node(k, indent + 1)
        else:
            lines.append(f"{pad}  End Site")
            lines.append(f"{pad}  {{")
            lines.append(f"{pad}    OFFSET 0.000000 5.000000 0.000000")
            lines.append(f"{pad}  }}")
        lines.append(f"{pad}}}")

    write_node(0, 0)
    
    # Motion section
    lines.append("MOTION")
    lines.append(f"Frames: {num_frames}")
    lines.append("Frame Time: 0.0333333")
    
    for f in range(num_frames):
        row = []
        # Root translation in cm
        rx, ry, rz = root_data[f]
        row.extend([f"{rx*100:.6f}", f"{ry*100:.6f}", f"{rz*100:.6f}"])
        
        # Rotations in ZXY Euler degrees
        for j in range(len(SOMA30_NAMES)):
            qx, qy, qz, qw = rot_data[f, j]
            q = mathutils.Quaternion((qw, qx, qy, qz))
            euler = q.to_euler('ZXY')
            row.extend([f"{np.degrees(euler.z):.6f}", f"{np.degrees(euler.x):.6f}", f"{np.degrees(euler.y):.6f}"])
            
        lines.append(" ".join(row))
        
    output_bvh.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported BVH: {output_bvh}")

if __name__ == "__main__":
    item_dir = Path(r"E:\Kimodo-CPP\demo-output\5e15f54638196203")
    output_bvh = item_dir / "motion.bvh"
    export_bvh(item_dir, output_bvh)
