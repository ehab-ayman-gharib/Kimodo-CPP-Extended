import numpy as np
import mathutils
from pathlib import Path

# Check any generated animation directory
dirs = list(Path(r"E:\Kimodo-CPP\demo-output").glob("*"))
for d in sorted(dirs, key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
    if (d / "root_positions.f32").exists():
        root_data = np.fromfile(d / "root_positions.f32", dtype=np.float32).reshape((-1, 3))
        print(f"\nDirectory: {d.name} ({len(root_data)} frames)")
        print(f"  Frame 0:   X={root_data[0,0]:.3f}, Y(Up)={root_data[0,1]:.3f}, Z(Fwd)={root_data[0,2]:.3f}")
        print(f"  Frame 30:  X={root_data[30,0]:.3f}, Y(Up)={root_data[30,1]:.3f}, Z(Fwd)={root_data[30,2]:.3f}")
        print(f"  Max Height variation in Y: {np.ptp(root_data[:,1]):.3f} m")
        print(f"  Max Forward travel in Z:   {np.ptp(root_data[:,2]):.3f} m")
