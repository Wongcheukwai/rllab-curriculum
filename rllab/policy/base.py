from rllab.misc import autoargs
from rllab.core.parameterized import Parameterized
import tensorfuse as theano
import tensorfuse.tensor as TT


class Policy(Parameterized):

    def __init__(self, mdp):
        self._observation_shape = mdp.observation_shape
        self._observation_dtype = mdp.observation_dtype
        self._action_dim = mdp.action_dim
        self._action_dtype = mdp.action_dtype

    # Should be implemented by all policies

    def get_actions(self, observations):
        raise NotImplementedError

    def get_action(self, observation):
        actions, pdists = self.get_actions([observation])
        return actions[0], pdists[0]

    @property
    def observation_shape(self):
        return self._observation_shape

    @property
    def observation_dtype(self):
        return self._observation_dtype

    @property
    def action_dim(self):
        return self._action_dim

    @property
    def action_dtype(self):
        return self._action_dtype

    @classmethod
    @autoargs.add_args
    def add_args(cls, parser):
        pass

    @classmethod
    @autoargs.new_from_args
    def new_from_args(cls, args, mdp):
        pass


class DeterministicPolicy(Policy):

    def get_action_sym(self, input_var):
        raise NotImplementedError


class StochasticPolicy(Policy):

    def __init__(self, mdp):
        super(StochasticPolicy, self).__init__(mdp)
        self._f_log_prob = None

    def kl(self, old_pdist_var, new_pdist_var):
        raise NotImplementedError

    def likelihood_ratio(self, old_pdist_var, new_pdist_var, action_var):
        raise NotImplementedError

    def compute_entropy(self, pdist):
        raise NotImplementedError

    # Only needed for vanilla policy gradient & guided policy search
    def get_log_prob(self, observations, actions):
        if self._f_log_prob is None:
            input_var = TT.tensor(
                'input',
                ndim=len(self.observation_shape) + 1,
                dtype=self.observation_dtype
            )
            action_var = TT.matrix('actions', dtype=self.action_dtype)
            self._f_log_prob = theano.function(
                [input_var, action_var],
                self.get_log_prob_sym(input_var, action_var),
                allow_input_downcast=True,
                on_unused_input='ignore'
            )
        return self._f_log_prob(observations, actions)

    def get_log_prob_sym(self, input_var, action_var):
        raise NotImplementedError

    def get_pdist_sym(self, input_var):
        raise NotImplementedError