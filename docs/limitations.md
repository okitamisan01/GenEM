# Scope and limitations

| Area | Current status |
|---|---|
| GenEM-inspired workflow | language-to-parameterized skills and iterative feedback; independent implementation |
| Mock | six skills, five scenarios, greeting aliases, validation and JSONL history verified |
| ROS 2 head adapter | implemented using FollowJointTrajectory; current-state preflight, bounded cubic waypoint compilation, per-plan confirmation, result checking and cancellation |
| Controller integration | real Jazzy JTC + two-joint GenericSystem tested; streamed excursions and final positions checked; loss of broadcaster triggered confirmed cancellation |
| Physical HSR | no actuation attempted; robot-specific reviewed profile and on-site commissioning still required |
| Full TeamSOBITS Gazebo HSR | Jazzy source inspected and connection profile provided; not built or run here |
| Live LLM / GPU / second PC | not tested |
| Perception, real speech, base/arms | not implemented; ROS speech steps reject the whole plan |

Mock estimates and hardware trajectory budgets differ. ROS motion is time-scaled
to the reviewed profile velocity/acceleration bounds and checked again as a whole.
These are command-space checks, not guarantees of collision clearance, physical
acceleration tracking or safety certification. The probe needs both position and
velocity feedback; deployments not providing them must be adapted and verified first.

Simulator mode checks for a recognized fake/Gazebo head hardware plugin to reduce
misrouting to a physical robot. Hardware mode still depends on a laboratory-reviewed
profile; the repository example deliberately remains unverified. ROS 2 alone does
not guarantee controller-manager compatibility across distributions or proprietary stacks.

A current-state check cannot guarantee exclusive controller ownership. Do not run
another head-command client concurrently. Software cancellation may fail during
communication loss; a supervised independent emergency stop remains necessary.

`look_at(person)` is a named direction, not tracked perception. The simulator preset
uses the known forward demo direction; the physical template has no person target.
`look_direction` uses absolute joint pan/tilt, not Cartesian gaze coordinates.

The default generator is deterministic and supports a small English vocabulary.
API calls are mocked in tests. No original multi-stage GenEM prompt pipeline,
learned-skill library, feedback router or human-subject evaluation is reproduced.
History is single-process local JSONL, with no database or concurrent-writer lock.

The Docker base is pinned; apt/rosdep repositories are not snapshot-locked. Linux
amd64 was tested; other architectures, Docker Desktop and GPU were not. Full Gazebo
HSR dependencies are intentionally separate from the lightweight client/test image.
