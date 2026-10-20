# Third-party references

The Docker configuration is independently written after studying TeamSOBITS/docker_ws.
No upstream scripts or Dockerfiles are vendored. Its BSD-3-Clause license was
checked at local revision `26c79cfb9ac0cfe1818e5b686d4e820e62dc5cc7`.
For attribution, the reference license is reproduced below. This does not imply endorsement.

The GenEM paper, appendices and videos are linked, not redistributed. No research
code was copied. ROS, Ubuntu and installed dependencies retain their own licenses;
consult their image/package metadata when redistributing container images.

## TeamSOBITS/docker_ws reference license

```text
BSD 3-Clause License

Copyright (c) 2025, TeamSOBITS

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## HSR ROS 2 integration references

The TeamSOBITS/hsrb_simulator Jazzy branch at
`a4eca087da629b8448fbc2a9adb3227e274f8288` was cloned into a temporary directory
for source/README inspection. No source or patches from it were vendored, modified
or pushed. The two-joint test URDF/configuration and trajectory compiler are newly
written here; ros2_control/control_msgs packages remain under their upstream licenses.
