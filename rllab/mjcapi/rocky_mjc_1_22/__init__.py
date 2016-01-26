from .mjviewer import MjViewer
from .mjcore import MjModel
from .mjcore import register_license
import os
from mjconstants import *

register_license(os.path.join(os.path.dirname(__file__),
                              '../../../private/mujoco/binaries/1_22/mjkey.txt'))
