# Robot Arm — Part Design Guide (Cheat Sheet #2)

Companion to `CAD_Cheat_Sheet.md`. That one tells you **what** the arm is.
This one tells you **how to actually model each part**, click by click.

---

## 0. Read this first — the trick that saves you

You don't have the servos in front of you, so every servo number below is
**published data, not your calipers.** Real servos vary by ±0.5 mm between
batches, and the cheap ones vary more.

Instead of waiting, we do this: **every servo dimension lives in one place —
a list of Global Variables.** Your sketches reference the variable names, not
the raw numbers. When your servos arrive and you measure them, you change six
numbers in one dialog and *every part in the whole arm updates itself.*

This takes 10 extra minutes today and saves you a full re-model later. Do it.

**Confidence tags used below:**

| Tag | Meaning |
|---|---|
| ✅ | Confirmed from datasheets. Safe to model with. |
| ⚠️ | Widely-used community value, but I could not confirm it from a manufacturer drawing. **Measure before you print.** |

---

## 1. Your servos — the numbers

### Which servo goes where

| Ch | Joint | Servo | Why |
|---|---|---|---|
| 0 | Base yaw | MG90S | Bearing carries the weight, servo only spins |
| 1 | Shoulder pitch | **DS3218** (270°) | Lifts the entire arm — biggest load |
| 2 | Elbow pitch | **DS3218** (270°) | Lifts forearm + wrist + gripper |
| 3 | Wrist roll | MG90S | Far from shoulder → must be light |
| 4 | Wrist pitch | MG90S | Same |
| 5 | Gripper | MG90S | Same |

### MG90S (micro servo — 4 of these)

| Dimension | Value | Tag |
|---|---|---|
| Body length | 22.8 mm | ✅ |
| Body width | 12.2 mm | ✅ |
| Body height (bottom → top of case, no shaft) | 28.5 mm | ✅ |
| Overall height incl. output shaft | 32.1 mm | ✅ |
| Overall length across mounting tabs | 32.5 mm | ✅ |
| Mounting hole spacing (centre-to-centre) | ~28 mm | ⚠️ |
| Mounting hole diameter | ~2.2 mm (M2 screws) | ⚠️ |
| Tab thickness | ~2.5 mm | ⚠️ |
| Height from base to underside of tabs | ~18.5 mm | ⚠️ |
| Output spline | 25T, ~4.8 mm OD | ⚠️ |
| Weight | 13.4 g | ✅ |
| Stall torque | 1.8 kg·cm @4.8 V / 2.2 kg·cm @6.6 V | ✅ |

### DS3218 (standard servo — 2 of these)

| Dimension | Value | Tag |
|---|---|---|
| Body length | 40 mm | ✅ |
| Body width | 20 mm | ✅ |
| Body height (bottom → top of case, no shaft) | 40.5 mm | ✅ |
| Overall length across mounting tabs | ~54 mm | ⚠️ |
| Mounting hole spacing (centre-to-centre) | ~49.5 mm | ⚠️ |
| Mounting hole diameter | ~4.5 mm w/ grommets, 3 mm bare (M3) | ⚠️ |
| Tab thickness | ~3 mm | ⚠️ |
| Height from base to underside of tabs | ~27 mm | ⚠️ |
| Output spline | 25T, ~6 mm OD | ⚠️ |
| Weight | 60 g | ✅ |
| Stall torque | 20 kg·cm @6.8 V (~17 kg·cm @6 V) | ✅ |

> **Sanity check I ran on your design:** with the arm stretched straight out
> horizontally — the worst case — the shoulder sees roughly **5 kg·cm** from the
> arm's own weight, plus about **3.5 kg·cm** if it's holding a 100 g object.
> That's ~8.5 kg·cm against ~17 kg·cm available. **About 2× margin — you're fine,
> but not luxuriously so.** Two consequences: keep printed parts light (infill
> 20 %, not solid), and treat **100 g as your realistic payload ceiling.**
>
> The tighter one is the **wrist pitch MG90S**: gripper + 100 g payload puts it
> near 1 kg·cm against 1.8 kg·cm stall. Stall torque is a *breaking* number, not
> a working one — plan on using half of it. If the wrist sags, that's the joint
> to blame, and the fix is a lighter gripper, not a bigger payload.

---

## 2. Set up your Global Variables (do this once, before any modeling)

In a **new part file**:

1. Menu bar → **Tools → Equations…**
2. Click into the **Global Variables** section (top box).
3. Type each name in the left column and its value on the right. Add these:

```
mg_L        = 22.8      ' MG90S body length
mg_W        = 12.2      ' MG90S body width
mg_H        = 28.5      ' MG90S body height
mg_holes    = 28        ' MG90S mounting hole spacing
mg_holeD    = 2.2       ' MG90S mounting hole diameter

ds_L        = 40        ' DS3218 body length
ds_W        = 20        ' DS3218 body width
ds_H        = 40.5      ' DS3218 body height
ds_holes    = 49.5      ' DS3218 mounting hole spacing
ds_holeD    = 3         ' DS3218 mounting hole diameter

clr         = 0.4       ' clearance around servo pockets
wall        = 3         ' standard wall thickness
upperArm    = 150       ' shoulder → elbow
foreArm     = 130       ' elbow → wrist
```

4. **OK.**
5. **File → Save As →** `_ArmGlobals.SLDPRT` in your project folder. Keep this file.

**To use a variable in a sketch:** when the Smart Dimension box pops up asking
for a number, type `=` first. A dropdown of your variables appears — pick one.
So a servo pocket length is typed as `= "mg_L" + "clr"`, not `23.2`.

**To share them with every other part:** in each new part, **Tools → Equations →
Import…** → pick `_ArmGlobals.SLDPRT`. Now changing that one file updates
everything. (Tick **Link to external file** so the connection stays live.)

> If this feels like too much on your first part, it's fine to skip it and type
> raw numbers — just know you're signing up to redo sketches later. My advice:
> do it. It's one dialog box.

---

## 3. The servo pocket recipe (you'll use this 6 times)

Every bracket in this arm is fundamentally *a box with a servo-shaped hole in it.*
Learn this once and five of the eight parts become easy.

**The recipe:**

1. Sketch a rectangle the size of the servo body **plus clearance on each side**:
   length `= "mg_L" + "clr"`, width `= "mg_W" + "clr"`.
   (Clearance goes on the total, not per side — 0.4 mm total gap is right for FDM.)
2. **Extrude Cut** it through the bracket wall, **Through All**.
3. Sketch the **two mounting holes** on the face the tabs will sit against:
   two circles, diameter `= "mg_holeD"`, separated by `= "mg_holes"`,
   symmetric about the pocket centre. Extrude Cut → Through All.
4. Sketch a **shaft clearance hole** on the opposite wall: a circle ~2 mm larger
   than the spline OD, centred on where the shaft lands. Extrude Cut → Through All.
5. Add a **0.5 mm fillet** to the pocket's inside vertical corners. Printers
   round inside corners anyway; if you don't model it, the servo won't seat flat.

**The three rules that make pockets actually fit:**

- **Clearance is 0.4 mm total, not per side.** Too loose and the servo rattles,
  which becomes visible jitter at the gripper.
- **The tabs, not the pocket, hold the servo.** The pocket locates it; the two
  screws carry the load. Never rely on friction.
- **Print a 15 mm-tall test slice of any pocket before printing the full part.**
  Five minutes of printing saves three hours.

---

## 4. Part-by-part walkthrough

Build in this order. Each part hands an interface to the next.

---

### Part 1 — Base (axis 1 housing)

**What it is:** a 120 mm square box. Holds the base MG90S pointing straight up,
and provides the bolt pattern for the lazy-Susan bearing on its top face.

**Why first:** it's flat, it's forgiving, and nothing hangs off it. It's where
you learn Extrude Boss and Extrude Cut without consequences.

1. **New Part → Top Plane → Sketch.**
2. **Corner Rectangle**, roughly centred on the origin. Smart Dimension both
   sides to **120 mm**. Add a **Midpoint** relation from a corner to the origin
   so the square is centred (fully defined = black lines).
3. **Features → Extrude Boss/Base → 40 mm.** You now have a solid block.
4. **Shell it out** so it isn't a 570 g brick: **Features → Shell → 3 mm**,
   and select the **top face** as the face to remove. You get an open-topped box.
5. **Servo pocket, vertical.** Select the **inside bottom face → Sketch.**
   Draw a rectangle `= "mg_L" + "clr"` × `= "mg_W" + "clr"`, centred on the origin.
   **Extrude Cut → Through All.** The servo now drops in from above, shaft up.
6. **Servo mounting holes.** The MG90S tabs sit ~18.5 mm up from its base, so the
   servo needs a **ledge** to hang from rather than sitting on the floor.
   Easiest version: sketch a rectangle 3 mm larger than the pocket on all sides
   on the *top* face of the floor, and Extrude Cut **down 18.5 mm** — now the
   servo body drops through and the tabs rest on the resulting shoulder.
   Then two holes, `= "mg_holeD"`, spaced `= "mg_holes"`, cut through that ledge.
7. **Bearing bolt pattern, top face.** ⚠️ **Leave this until the bearing arrives.**
   4" lazy Susans vary — the hole pattern is *not* standardised. Model everything
   else and add these holes last. When it arrives, measure the hole spacing and
   cut four holes for M4.
8. **Cable exit.** One 12 mm hole in a side wall, near the bottom. Do not skip
   this — six servo cables have to leave the base somewhere, and drilling it
   into a finished print goes badly.
9. **Fillet** the four outside vertical edges, 3 mm. Looks better, prints better.

**Print notes:** flat on its open face, no supports needed, 20 % infill.
This is your biggest print (~4 hrs) — run it while modeling Part 2.

---

### Part 2 — Rotating platform

**What it is:** a disc that sits on the bearing's top ring and is driven by the
base servo's shaft. Everything above this rotates.

**The one thing that matters here:** the bearing carries the weight; the servo
only turns it. If the servo shaft ends up carrying the arm's mass, the base
servo dies within a week.

1. **Top Plane → Sketch → Circle**, centred on origin, **diameter 110 mm.**
2. **Extrude Boss → 5 mm.**
3. **Bearing holes:** same ⚠️ pattern as Part 1 step 7 — wait for the bearing,
   then mirror the identical bolt circle onto the underside.
4. **Servo horn mount, centre.** Don't try to model the 25T spline — you'll never
   get it right and you don't need to. Instead: use the **plastic horn that came
   with the servo.** Sketch a circle **22 mm** diameter at the origin and
   Extrude Cut **2 mm deep** — a shallow recess for the horn to sit in. Then four
   **2 mm** holes matching the horn's own screw holes ⚠️ (measure the horn),
   cut Through All. You screw the horn to the platform, then the horn clips to
   the servo spline. This is how nearly every hobby robot does it.
5. **Shoulder bracket mounting holes:** four **3.5 mm** holes in a 40 × 40 mm
   square, centred. Part 3 bolts down onto these.

**Print notes:** flat, 30 % infill (this one takes real load), 4 top/bottom layers.

---

### Part 3 — Shoulder bracket (axis 2)

**What it is:** a **U-shaped yoke** standing on the platform, holding the DS3218
horizontally so its shaft points sideways. The upper arm pivots on that shaft.

**This is the first part that's genuinely structural.** The shoulder carries the
whole arm, and the DS3218 shaft is only supported on one side — so the opposite
side needs a **matching idler pivot** or the joint will wobble and eventually
crack. Both walls of the U, always.

1. **Front Plane → Sketch** a U: outer 60 mm wide × 70 mm tall, with a
   40 mm-wide × 50 mm-tall rectangle removed from the top centre. Two uprights,
   ~10 mm each, joined by a base.
2. **Extrude Boss → 45 mm** (deep enough that the DS3218 fits between the walls
   — check: `ds_L` is 40 mm, so 45 gives 2.5 mm each side. Good).
3. **Servo pocket in the left upright.** Select its inner face → Sketch a rectangle
   `= "ds_L" + "clr"` × `= "ds_H" + "clr"`. **Extrude Cut → Through All.**
   Note the orientation: the servo lies on its side, shaft pointing right.
4. **Mounting holes:** two circles `= "ds_holeD"`, spaced `= "ds_holes"`,
   on the outer face of that upright. Through All.
5. **Idler pivot in the right upright.** Sketch a circle **8 mm** diameter,
   *concentric with the servo shaft axis* — use a construction line across from
   the pocket centre to guarantee they're on the same axis. Extrude Cut Through All.
   An 8 mm bearing or a smooth M8 bolt goes here.
   **If these two axes don't line up, the joint binds.** Take the extra minute.
6. **Base flange:** four 3.5 mm holes matching Part 2's 40 × 40 pattern.
7. **Fillets, 3 mm**, where each upright meets the base. This is the highest-stress
   corner in the entire arm — a sharp corner here will crack. Don't skip it.

**Print notes:** upright, on its base flange. Needs supports under the pocket.
**40 % infill and 5 perimeters** — this part earns it.

---

### Part 4 — Upper arm (150 mm)

**What it is:** the beam from shoulder to elbow. Two parallel side plates, not a
solid bar — you want stiffness without mass.

1. **Front Plane → Sketch** a rounded rectangle: **150 mm long × 30 mm tall.**
   Use the **Slot** tool (straight slot, 150 mm centres, 30 mm width) — it gives
   you rounded ends for free, which is exactly what a link wants.
2. **Extrude Boss → 4 mm.** That's one side plate.
3. **Shoulder end:** a 25 mm circular recess, 2 mm deep, for the DS3218 horn,
   plus horn screw holes ⚠️ (measure your horn). Same approach as Part 2.
4. **Elbow end:** the elbow servo pocket. Cut `= "ds_L" + "clr"` ×
   `= "ds_H" + "clr"` and its two mounting holes, exactly as in Part 3.
5. **Lightening holes:** three **20 mm** circles evenly spaced along the middle.
   Extrude Cut Through All. Removes ~15 g at almost no stiffness cost — and at
   150 mm from the shoulder, every gram counts double.
6. **Mirror it.** You need a second plate for the other side. **Insert → Mirror
   Part**, or just save-as and delete the servo pocket (only one plate holds the
   servo; the other gets the 8 mm idler hole).
7. **Two spacers:** simple 25 mm-long tubes, 8 mm OD / 4 mm ID, that bolt the two
   plates together at the right separation. Model as one part, print two.

**Print notes:** flat on the bed, 25 % infill, **rotate 45° in the slicer** so
layer lines don't run straight across the beam — that's the direction it snaps.

---

### Part 5 — Elbow bracket + forearm (130 mm)

**Structurally identical to Part 4, just shorter.** Copy the file, change the
slot length from 150 to 130, done. (If you set up global variables, change
`foreArm` and it updates itself — this is the payoff moment.)

Two differences:

- The **elbow end** takes the DS3218 horn recess (mirror of Part 4's elbow pocket).
- The **wrist end** takes an **MG90S** pocket, not a DS3218 — much smaller.
  Cut `= "mg_L" + "clr"` × `= "mg_H" + "clr"`.

**Weight discipline starts here.** Everything past the elbow is a lever arm on the
shoulder. 20 % infill, 3 perimeters, and add lightening holes wherever the part
isn't obviously carrying load.

---

### Part 6 — Wrist (axes 4 + 5)

**Build this LAST, after the arm below it moves.** It's the hardest part in the
project — two servos packed into ~45 mm with their axes at 90° to each other —
and the mounting details depend on how the finished forearm actually sits.

**Concept:** a small U-yoke (pitch, from the forearm) carrying a rotating cup
(roll, driving the gripper).

1. **Pitch yoke** — same U-bracket recipe as Part 3, scaled to the MG90S:
   outer ~30 mm wide × 35 mm tall, walls 4 mm, pocket `= "mg_L" + "clr"` ×
   `= "mg_H" + "clr"`, idler hole 4 mm on the opposite wall.
2. **Roll housing** — a cylinder ~28 mm OD × 30 mm long, hollow, with an MG90S
   pocket cut into its side. It bolts to the pitch yoke's output horn.
3. **Gripper interface** — a flat plate on the roll servo's horn with four
   M2 holes on a 20 × 20 mm square for Part 7.

**Expect to print this three times.** Everyone does. That's why it's last — by
then you'll have real calipered servo dimensions and a working arm to test against.

---

### Part 7 — Gripper (axis 6)

**Build last.** A single MG90S driving two jaws through a linkage.

**The simplest mechanism that works** — and the one to use for v1 — is a **pair
of meshing gear sectors**: each jaw has gear teeth cut on a 20 mm-radius arc at
its pivot; the servo drives one jaw, the meshed teeth drive the other in mirror.
One servo, symmetric grip, no linkage bars to bind.

- Two jaws, ~50 mm long, 4 mm thick, pivoting on 3 mm pins ~35 mm apart.
- SolidWorks has **Toolbox gears** (`Design Library → Toolbox → Power Transmission
  → Gears`); use a spur gear, module 1.5, and cut it down to a ~60° sector.
- Line the gripping faces with a strip of TPU or glued-on rubber. Rigid PLA on
  a rigid object grips essentially nothing.

**Don't over-engineer v1.** Print the simplest jaws that close, find out what
actually fails, then improve. First grippers are always wrong in a way you can't
predict from CAD.

---

## 5. Print settings summary

| Part | Orientation | Infill | Perimeters | Supports |
|---|---|---|---|---|
| Base | Open side down | 20 % | 3 | No |
| Platform | Flat | 30 % | 4 | No |
| Shoulder bracket | Upright on flange | **40 %** | **5** | Yes |
| Upper arm ×2 | Flat, rotated 45° | 25 % | 3 | No |
| Forearm ×2 | Flat, rotated 45° | 20 % | 3 | No |
| Wrist | Yoke opening up | 30 % | 4 | Yes |
| Gripper jaws | Flat | 30 % | 4 | No |

**Material:** PLA is fine for v1 and easiest to print. PETG if the arm will run
warm or live somewhere hot. Skip ABS — the warping isn't worth it on parts this size.

**Layer height:** 0.2 mm everywhere, except gripper gear teeth at 0.15 mm.

---

## 6. Before you print anything — checklist

- [ ] Servos arrived and **all ⚠️ dimensions re-measured** with calipers
- [ ] Global variables updated with the real numbers
- [ ] Lazy-Susan bearing measured, bolt patterns added to Parts 1 and 2
- [ ] Servo horns measured, recesses and screw holes updated
- [ ] Test-printed one servo pocket slice and confirmed the fit
- [ ] Shoulder bracket: verified the servo shaft axis and idler hole are concentric
- [ ] Every inside corner has a fillet

---

## 7. If you get stuck

**"My sketch lines are blue, not black."** Under-defined — it's missing dimensions
or relations. Usually add a Midpoint relation to the origin. Blue sketches move
on you when you edit something else; fix them early.

**"Extrude Cut isn't cutting."** The sketch isn't on the face you think it is, or
the direction is flipped. Tick **Reverse Direction**, or use **Through All — Both**.

**"The part looks right but nothing fits."** You almost certainly applied clearance
per side instead of to the total, so the pocket is 0.4 mm too big in each direction.

**"Where do I even start today?"** Part 1, step 1. A 120 mm square on the Top Plane.
Everything else follows from having done one thing.

---

*Sources for servo specifications:*
- [MG90S datasheet — TowerPro](https://www.electronicoscaldas.com/datasheet/MG90S_Tower-Pro.pdf)
- [MG90S specifications — Components101](https://components101.com/motors/mg90s-metal-gear-servo-motor)
- [DS3218 datasheet](https://autoctrls.com/ds3218-datasheet/)
- [DS3218 specifications — ThinkRobotics](https://thinkrobotics.com/products/ds3218-servo)
- [MG996R mechanical drawing (same standard case as DS3218)](https://www.handsontec.com/dataspecs/motor_fan/MG996R.pdf)
