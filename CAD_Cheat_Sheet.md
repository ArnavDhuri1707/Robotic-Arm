# Robot Arm — CAD Cheat Sheet

A one-page reference for modeling the arm in SolidWorks. Keep it open next to CAD.

---

## 1. The numbers (what you're building)

| Part | Size | Notes |
|---|---|---|
| Total reach | ~35 cm | Shoulder to fingertip, stretched straight |
| Upper arm (shoulder→elbow) | 15 cm | |
| Forearm (elbow→wrist) | 13 cm | Kept shorter to keep weight near the shoulder |
| Gripper (wrist→fingertip) | ~7 cm | |
| Base | 120 × 120 mm square | Room for the 100 mm bearing + margin |
| Bearing | 4" (100 mm) metal lazy Susan | Carries the arm's weight |

**6 servos total** — five moving joints + the gripper.

| # | Joint | Motion | Where |
|---|---|---|---|
| 1 | Base | yaw (spin left/right) | base |
| 2 | Shoulder | pitch (lift up/down) | shoulder |
| 3 | Elbow | pitch (bend) | elbow |
| 4 | Wrist | pitch (tilt up/down) | wrist |
| 5 | Wrist | roll (spin the gripper) | wrist |
| 6 | Gripper | open/close | end |

**Joints 4-5 are the wrist** — two small servos packed close together, plus the gripper servo right after. This cluster is the hardest part to design, so build it **last**. Use small servos here (MG90S-class) to keep the end light.

---

## 2. Plain-English glossary

- **Joint** — a place the arm bends or turns. Each has one servo.
- **Yaw / Pitch** — Yaw = turning left/right (like shaking your head "no"). Pitch = tilting up/down (nodding "yes"). The base does yaw; the shoulder, elbow, wrist do pitch.
- **Servo** — the motor. It turns to a commanded angle. It has a rectangular body, two mounting tabs with screw holes, and a splined output shaft on top.
- **Servo horn** — the plastic/metal arm that clips onto the servo shaft and bolts to the next part. This is how a servo connects to the thing it moves.
- **Spline** — the ring of tiny teeth on the servo shaft (yours is 25 teeth / "25T"). The horn's teeth mesh with it so it can't slip.
- **Bearing** — two rings with balls between them: one ring stays still, the other spins smoothly. It carries weight so the servo doesn't have to.
- **Coupling** — any part that joins two things so they turn together (e.g. platform-to-servo-shaft).
- **Tolerance / clearance** — the deliberate tiny gap you leave between two printed parts so they actually fit. Plastic prints a hair fat, so holes need to be slightly bigger than the peg. Start with **0.2–0.4 mm** gap.
- **Fillet** — a rounded inside corner. Sharp inside corners crack; a fillet spreads the stress. Add small fillets where a part meets a thin wall.

## 3. SolidWorks moves you'll use 90% of the time

- **Sketch** → draw a 2D shape on a flat plane (Top / Front / Right).
- **Extrude Boss** → push a sketch out into a solid (makes material).
- **Extrude Cut** → push a sketch *through* a solid (removes material — this is how you make holes and pockets).
- **Smart Dimension** → type in exact sizes so nothing is guessed.
- **Fillet / Chamfer** → round or bevel edges.
- Work in **millimeters** (check bottom-right of the screen). Save often.

---

## 4. Five golden rules for this arm

1. **Design around the servo — get its real dimensions first.** Every bracket is basically a box that hugs a servo. Measure the servo body, tab spacing, and shaft position with calipers (or grab the datasheet) *before* modeling the bracket.
2. **Model each servo as a simple block first.** Make a plain rectangular "stand-in" the exact size of the real servo. Build your bracket around that block, then cut a pocket for it. This keeps fits honest.
3. **The bearing carries weight, the servo only turns.** Never hang a heavy part directly off a servo shaft — support it with a bearing or a pin, and let the servo just drive rotation.
4. **Keep weight close to the shoulder.** Heavier servos (elbow, wrist) tucked inward; lighter parts out toward the gripper. Long + heavy at the end = the shoulder can't hold it up.
5. **Leave clearance on every printed fit.** 0.2–0.4 mm gap for pegs/holes, ~0.5 mm around servo pockets. Print a small test fit before committing to a big part.

---

## 5. Build order (model in this sequence)

Do them one at a time. Each part hands an interface to the next, so building in order means fewer redo's.

1. **Base** (axis 1) — 120 mm box, pocket for the yaw servo, holes for the lazy-Susan bearing.
2. **Rotating platform** — sits on the bearing, couples to the yaw servo shaft.
3. **Shoulder bracket** (axis 2) — holds the shoulder servo; this is what the platform carries.
4. **Upper arm** (15 cm) — connects shoulder servo to the elbow.
5. **Elbow bracket + forearm** (joint 3, 13 cm) — elbow servo to the forearm.
6. **Wrist** (joints 4 + 5) — two small servos: pitch (tilt) then roll (spin). The tricky compact part — take your time here.
7. **Gripper** (joint 6) — build **last**, once the arm moves.

*Note: the wrist + gripper servos sit far from the shoulder. Keep them small, and if the "hand" section grows to fit them, trim the forearm a cm or two to keep total reach near 35 cm.*

---

## 6. Measure these with calipers before modeling each bracket

For every servo: **body length × width × height**, **distance between the two mounting-tab screw holes**, **screw hole diameter**, **shaft position** (from body edge), and **shaft height** above the body. For the bearing when it arrives: **plate size** and **distance between the mounting screw holes**.

---

*Rule of thumb if unsure: make the pocket 0.3 mm bigger than the part, round inside corners, and print a small test piece before the full part.*
