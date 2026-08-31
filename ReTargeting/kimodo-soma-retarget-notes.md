# Kimodo motion onto a real rig: the tool, and the format behind it

Two parts. **Part one** is the two-script tool that takes a Kimodo clip and
leaves you an Anim Sequence on the Unreal mannequin. **Part two** is the raw
format, for anyone writing their own transfer into Blender, Maya or a custom
rig.

If you just want the motion on a character, part one is the whole answer and you
can stop reading after it.

---

# Part 1: the tool

Two steps. The first runs on your desktop and needs nothing but Python 3.8 or
newer, no Blender and no extra packages. The second runs inside Unreal and needs
nothing but a project with the Third Person template content in it.

## Step 1: clip to file

```
python kimodo_to_glb.py path/to/clip
```

`path/to/clip` is the folder Kimodo writes for one animation. It holds:

```
local_rotations_xyzw.f32     the joint rotations
root_positions.f32           where the hips are, in metres
prompt.txt                   optional, only used to name the output
```

You get a `.glb` next to the script. Several clips at once works too:

```
python kimodo_to_glb.py clips/* --outdir glb
```

| Option | What it does |
|---|---|
| `-o walk.glb` | name the output file, one clip at a time |
| `--outdir glb` | put the outputs in this folder |
| `--fps 24` | frame rate, default 30, which is what Kimodo generates |
| `--names native` | keep Kimodo's own bone names instead of the mannequin ones |

## Step 2: file to character

In Unreal, open the Output Log, switch the input box at the bottom from Cmd to
Python, and paste:

```
py "C:/path/to/unreal_retarget.py" "C:/path/to/walk_150.glb"
```

That imports the file, builds the IK Rig and the IK Retargeter, corrects the two
things that always need correcting, bakes, and leaves you an Anim Sequence at
`/Game/Kimodo/Retargeted/A_walk_150`.

Drop the mannequin into your level, set its Animation Mode to Use Animation
Asset, and pick that sequence.

Pass several `.glb` paths to do them in one go. Pass none and it converts every
`.glb` sitting next to the script. To use a different character, put its
Skeletal Mesh path last:

```
py ".../unreal_retarget.py" ".../walk_150.glb" /Game/MyChars/SK_Hero
```

It prints a line per clip so you can see it went well:

```
kick_120: SMPL-X, 22 joints
    9 chains mapped, 19 left at rest (Root, LeftThumb, ...)
    reach 102 cm to 95 cm, arms corrected by up to 48 deg
    arms match 0.998 (worst lowerarm_r), pelvis 93 cm, lowest toe -1 cm,
    travelled 123 cm over 4.0 s
```

**`arms match`** is how closely the character's arms point where the source's
arms pointed, sampled through the clip. Above 0.95 is good.
**`lowest toe`** should be near zero: much above and the character floats, much
below and it sinks.

## Skeletons

The joint count picks the skeleton, so there is nothing to configure. All three
retarget onto the mannequin.

| Joints | Skeleton | Notes |
|---|---|---|
| 22 | SMPL-X | bones are renamed to mannequin names, everything maps |
| 30 | SOMA | Mixamo-style names, everything maps |
| 34 | Unitree G1 | a robot: no clavicle, neck or head, so those four chains on the character keep their rest pose |

G1 is the one to watch. It splits each hip into three single-axis joints where
the mannequin has one, so hip rotation is partly lost, and it never predicted a
head orientation because it has no head. Arms and legs come across fine.

## What gets corrected, and why

Two things go wrong if you build the retargeter by hand and skip them, in ways
that are hard to trace back:

- **The source is half underground.** Kimodo puts the hips at the origin with
  the legs hanging below, so the rig starts sunk into the floor and the
  retargeter has no vertical range left. The script lifts it by the rest leg
  reach. Note *rest*, not the first animation frame: a clip that starts crouched
  would otherwise bake out standing upright.
- **The rest poses disagree.** The mannequin rests in an A-pose, Kimodo does
  not. Left alone the retargeter reads that gap as motion and the arms sit wrong
  for the whole clip. The script measures both and cancels it per arm segment,
  parent before child. It is usually worth 45 to 55 degrees.

## About the box rig

Step 1 produces a skeleton wearing a box per bone. That is scaffolding, not the
result. Unreal will not create a Skeletal Mesh from a file with no geometry in
it, and without a Skeletal Mesh there is nothing for the retargeter to read the
motion from. Step 2 is what turns it into a character. Once the bake is done you
can delete `/Game/Kimodo/Source` and keep only `/Game/Kimodo/Retargeted`.

If you only want the raw skeleton, step 1 alone is enough: drag the `.glb` into
the Content Browser and it imports on its own.

## If something goes wrong

`kimodo_to_glb.py` checks its own output before writing it. It rebuilds the pose
from the file it just made and compares that against the input, so a wrong axis,
a shuffled hierarchy or a quaternion in the wrong component order is caught
there rather than in Unreal. The number it prints is the worst joint
disagreement in metres and should be around `1e-08`.

| Message | Meaning |
|---|---|
| `not a kimodo clip directory` | wrong folder, or you pointed it at a `.glb` |
| `rotation and root files disagree` | the two files are from different runs, or one is truncated |
| `rotations are not unit quaternions` | that file is not Kimodo rotation data |
| `N joints matches no known skeleton` | a skeleton this version does not know |
| `no mannequin-style character found` | add the Third Person template content to the project, or pass a Skeletal Mesh path |

## Notes

Scale is metres and Unreal converts on import, so a character comes in at life
size. Kimodo's axes already are glTF's axes, so nothing is rotated or mirrored
on the way through.

Root motion is baked into the hip track, the way Kimodo produces it. There is no
separate root bone. If you need root motion in Unreal, enable Force Root Lock or
extract it yourself.

---

# Part 2: the raw format

Only needed if you are writing your own transfer. Everything below describes the
**SOMA 30-joint** skeleton, which is what `Kimodo-SOMA-RP-v1.1` and
`Kimodo-SOMA-SEED-v1.1` produce. Those two ship under the NVIDIA Open Model
License, so unlike SMPL-X they are usable in commercial work.

## What the command line writes

| File | Shape | Contents |
|---|---|---|
| `local_rotations_xyzw.f32` | `[FRAMES, 30, 4]` | Local rotations, XYZW quaternions |
| `root_positions.f32` | `[FRAMES, 3]` | Root translation in metres |

Little-endian float32, no header.

## The joint count trap

The published format table says `[FRAMES, 22, 4]`. That number is **SMPL-X
only**.

| Model | Joints | Bytes for a 90-frame clip |
|---|---|---|
| SMPL-X RP v1 | 22 | 31,680 |
| **SOMA RP / SEED v1.1** | **30** | **43,200** |
| G1 RP / SEED v1 | 34 | 48,960 |

`FRAMES x JOINTS x 4 x 4` bytes. Read a SOMA file with a 22-joint stride and
every frame after the first is offset by 32 floats. You do not get an exception.
You get an animation that looks like the rig is having a seizure, and you spend
an hour blaming the model.

**Always derive the joint count from the file size** rather than hardcoding it:

```python
import os
n_bytes = os.path.getsize("local_rotations_xyzw.f32")
n_root  = os.path.getsize("root_positions.f32")
frames  = n_root // 12                 # 3 floats x 4 bytes
joints  = n_bytes // (frames * 16)     # 4 floats x 4 bytes
```

## The SOMA hierarchy

Thirty joints. `parent = -1` marks the root.

| # | Joint | Parent | | # | Joint | Parent |
|---|---|---|---|---|---|---|
| 0 | Hips | - | | 15 | LeftHandMiddleEnd | 13 |
| 1 | Spine1 | 0 | | 16 | RightShoulder | 3 |
| 2 | Spine2 | 1 | | 17 | RightArm | 16 |
| 3 | Chest | 2 | | 18 | RightForeArm | 17 |
| 4 | Neck1 | 3 | | 19 | RightHand | 18 |
| 5 | Neck2 | 4 | | 20 | RightHandThumbEnd | 19 |
| 6 | Head | 5 | | 21 | RightHandMiddleEnd | 19 |
| 7 | Jaw | 6 | | 22 | LeftLeg | 0 |
| 8 | LeftEye | 6 | | 23 | LeftShin | 22 |
| 9 | RightEye | 6 | | 24 | LeftFoot | 23 |
| 10 | LeftShoulder | 3 | | 25 | LeftToeBase | 24 |
| 11 | LeftArm | 10 | | 26 | RightLeg | 0 |
| 12 | LeftForeArm | 11 | | 27 | RightShin | 26 |
| 13 | LeftHand | 12 | | 28 | RightFoot | 27 |
| 14 | LeftHandThumbEnd | 13 | | 29 | RightToeBase | 28 |

Coordinate frame is **Y-up, Z-forward**, right handed, metres. Rest orientations
are identity, so the rest pose is a T-pose and every animated global quaternion
is also the world-space delta from rest. That is the property that makes
retargeting cheap.

Jaw and the two eye joints carry no useful motion. Ignore them unless you have a
face rig that wants them.

## Mapping to Mixamo

SOMA does not use the SMPL-X naming convention at all. It uses **CamelCase names
that are almost exactly Mixamo's**, which is why a Mixamo transfer needs a name
map and very little else.

Most joints map by adding the `mixamorig:` prefix. Four do not:

| SOMA | Mixamo |
|---|---|
| `Chest` | `mixamorig:Spine2` |
| `LeftLeg` | `mixamorig:LeftUpLeg` |
| `LeftShin` | `mixamorig:LeftLeg` |
| `RightLeg` | `mixamorig:RightUpLeg` |
| `RightShin` | `mixamorig:RightLeg` |

**Read that leg block twice.** SOMA's `LeftLeg` is the thigh. Mixamo's
`LeftLeg` is the shin. The names collide and mean opposite bones, and a naive
prefix-only map produces a character whose knees bend from the hip. This is the
single most likely thing to go wrong.

`Neck1` and `Neck2` collapse onto `mixamorig:Neck` if your target has one neck
bone. The finger end joints and the eyes have no Mixamo counterpart on a
standard rig, so drop them.

## Applying it in Blender

The shape of the job, whichever way you script it:

1. Read the two `.f32` files, derive `frames` and `joints` from the sizes.
2. Build the name map above against your target armature.
3. For each frame, set each mapped bone's `rotation_quaternion` in **WXYZ**
   order. The file is **XYZW**, so reorder:
   `(w, x, y, z) = (q[3], q[0], q[1], q[2])`.
4. Apply `root_positions` to the hip bone's location. Values are metres, so
   multiply by 100 if your scene is in centimetres.
5. Insert keyframes at 30 fps and set the scene frame rate to match, or the
   motion plays at the wrong speed.

Two things that bite:

- **Bone roll.** If your target rig's rest pose is not a clean T-pose, identity
  rest orientations will not line up. Either rest-pose your target to a T first,
  or compute a per-bone correction quaternion once and apply it every frame.
  This is the same problem the Unreal script solves automatically, and it is
  worth 45 to 55 degrees on an A-pose rig.
- **Root motion.** Some clips travel a long way. If you want the animation in
  place, zero `root_positions` on X and Z and keep only Y.

## Practical limits

- Coherent output tops out at about **300 frames, or 10 seconds**. Past that the
  clip drifts and eventually collapses into noise. Generate segments and blend.
- Shorter clips are punchier. The same prompt at 120 frames reads as more
  athletic than at 300, because the model fills the extra time rather than
  repeating the action harder.
- 20 denoising steps is the working default. Higher costs linearly and does not
  visibly improve the motion.

---

## Licence

The SOMA and G1 checkpoints are under the
[NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/),
which permits commercial use. The joint names and parent graph above come from
Kimodo's own Apache-2.0 source. The SMPL-X checkpoint is a different licence
entirely, restricted to internal research, so do not assume anything you learn
here transfers to it commercially.
