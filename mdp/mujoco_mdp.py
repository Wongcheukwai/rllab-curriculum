from .base import ControlMDP
import os
from mjpy import MjModel, MjViewer
import numpy as np
from contextlib import contextmanager
import os.path as osp
import sys
import random

class MujocoMDP(ControlMDP):

    def __init__(self, model_path, horizon, frame_skip, ctrl_scaling):
        self.model_path = model_path
        self.model = MjModel(model_path)
        self.data = self.model.data
        self.viewer = None
        self.init_qpos = self.model.data.qpos
        self.init_qvel = self.model.data.qvel
        self.init_ctrl = self.model.data.ctrl
        self.qpos_dim = self.init_qpos.size
        self.qvel_dim = self.init_qvel.size
        self.ctrl_dim = self.init_ctrl.size
        self.frame_skip = frame_skip
        self.ctrl_scaling = ctrl_scaling
        self.reset()
        super(MujocoMDP, self).__init__(horizon)

    @property
    def observation_shape(self):
        return self.get_current_obs().shape

    @property
    def n_actions(self):
        return len(self.model.data.ctrl)

    def reset(self):
        self.model.data.qpos = self.init_qpos
        self.model.data.qvel = self.init_qvel
        self.model.data.ctrl = self.init_ctrl
        self.current_state = self.get_current_state()
        return self.get_current_state(), self.get_current_obs()

    def get_state(self, pos, vel):
        return np.concatenate([pos.reshape(-1), vel.reshape(-1)])

    def decode_state(self, state):
        qpos, qvel = np.split(state, [self.qpos_dim])
        #qvel = state[self.qpos_dim:self.qpos_dim+self.qvel_dim]
        return qpos, qvel

    def get_current_obs(self):
        raise NotImplementedError

    def get_obs(self, state):
        with self.set_state_tmp(state):
            return self.get_current_obs()

    def get_current_state(self):
        return self.get_state(self.model.data.qpos, self.model.data.qvel)

    def forward_dynamics(self, state, action, preserve=True):
        with self.set_state_tmp(state, preserve):
            self.model.data.ctrl = action * self.ctrl_scaling
            for _ in range(self.frame_skip):
                self.model.step()
            #self.model.forward()
            return self.get_current_state()

    def get_viewer(self):
        if self.viewer is None:
            self.viewer = MjViewer()
            self.viewer.start()
            self.viewer.set_model(self.model)
        return self.viewer

    def plot(self):
        viewer = self.get_viewer()
        viewer.loop_once()

    def start_viewer(self):
        viewer = self.get_viewer()
        if not viewer.running:
            viewer.start()

    def stop_viewer(self):
        if self.viewer:
            self.viewer.finish()

    @contextmanager
    def set_state_tmp(self, state, preserve=True):
        if np.array_equal(state, self.current_state) and not preserve:
            yield
        else:
            if preserve:
                prev_pos = self.model.data.qpos
                prev_qvel = self.model.data.qvel
                prev_ctrl = self.model.data.ctrl
                prev_act = self.model.data.act
            qpos, qvel = self.decode_state(state)
            self.model.data.qpos = qpos
            self.model.data.qvel = qvel
            self.model.forward()
            yield
            if preserve:
                self.model.data.qpos = prev_pos
                self.model.data.qvel = prev_qvel
                self.model.data.ctrl = prev_ctrl
                self.model.data.act = prev_act
                self.model.forward()


#class WalkerMDP(MjcMDP):
#
#    def __init__(self):
#        self.frame_skip = 4
#        self.ctrl_scaling = 20.0
#        self.timestep = .02
#        MjcMDP.__init__(self, osp.abspath(osp.join(osp.dirname(__file__), '../vendor/mujoco_models/walker2d.xml')))
#
#    def get_obs(self, state):
#        with self.set_state_tmp(state):
#            return np.concatenate([self.model.data.qpos, np.sign(self.model.data.qvel), np.sign(self.model.data.qfrc_constraint)]).reshape(1,-1)
#
#    @property
#    def observation_shape(self):
#        return self.sample_initial_state()[1].shape
#
#    @property
#    def n_actions(self):
#        return len(self.model.data.ctrl)
#
#    def step(self, a):
#
#        posbefore = self.model.data.xpos[:,0].min()
#        self.model.data.ctrl = a * self.ctrl_scaling
#
#        for _ in range(self.frame_skip):
#            self.model.step()
#
#        posafter = self.model.data.xpos[:,0].min()
#        reward = (posafter - posbefore) / self.timestep + 1.0
#
#        s = np.concatenate([self.model.data.qpos, self.model.data.qvel])
#        notdone = np.isfinite(s).all() and (np.abs(s[3:])<100).all() and (s[0] > 0.7) and (abs(s[2]) < .5)
#        done = not notdone
#
#        ob = self._get_obs()
#
#        return ob, reward, done