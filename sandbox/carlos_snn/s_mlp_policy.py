import lasagne
import lasagne.layers as L
import lasagne.nonlinearities as NL
import theano.tensor as TT
import numpy as np

from rllab.core.lasagne_layers import ParamLayer
from rllab.core.lasagne_powered import LasagnePowered
from rllab.core.network import MLP
from rllab.spaces import Box

from rllab.core.serializable import Serializable
from rllab.policies.base import StochasticPolicy
from rllab.misc.overrides import overrides
from rllab.misc import logger
from rllab.misc import ext
from rllab.misc import autoargs
from rllab.distributions.diagonal_gaussian import DiagonalGaussian


class GaussianMLPPolicy_snn(StochasticPolicy, LasagnePowered, Serializable):
    @autoargs.arg('hidden_sizes', type=int, nargs='*',
                  help='list of sizes for the fully-connected hidden layers')
    @autoargs.arg('std_sizes', type=int, nargs='*',
                  help='list of sizes for the fully-connected layers for std, note'
                       'there is a difference in semantics than above: here an empty'
                       'list means that std is independent of input and the last size is ignored')
    @autoargs.arg('initial_std', type=float,
                  help='Initial std')
    @autoargs.arg('std_trainable', type=bool,
                  help='Is std trainable')
    @autoargs.arg('output_nl', type=str,
                  help='nonlinearity for the output layer')
    @autoargs.arg('nonlinearity', type=str,
                  help='nonlinearity used for each hidden layer, can be one '
                       'of tanh, sigmoid')
    @autoargs.arg('bn', type=bool,
                  help='whether to apply batch normalization to hidden layers')
    def __init__(
            self,
            env_spec,
            ##CF - latent units a the bottom
            latent_dim = 2,
            latent_type='normal',
            hidden_sizes=(32, 32),
            learn_std=True,
            init_std=1.0,
            adaptive_std=False,
            std_share_network=False,
            std_hidden_sizes=(32, 32),
            std_hidden_nonlinearity=NL.tanh,
            hidden_nonlinearity=NL.tanh,
            output_nonlinearity=None,
    ):
        self.latent_dim = latent_dim  ##could I avoid needing this self for the get_action?
        self.latent_type=latent_type
        Serializable.quick_init(self, locals())
        assert isinstance(env_spec.action_space, Box)

        ##CF - enlarge obs with the latents
        obs_dim = env_spec.observation_space.flat_dim + latent_dim
        action_dim = env_spec.action_space.flat_dim

        # create network
        mean_network = MLP(
            input_shape=(obs_dim,),
            output_dim=action_dim,
            hidden_sizes=hidden_sizes,
            hidden_nonlinearity=hidden_nonlinearity,
            output_nonlinearity=output_nonlinearity,
        )

        l_mean = mean_network.output_layer
        obs_var = mean_network.input_var

        if adaptive_std:
            l_log_std = MLP(
                input_shape=(obs_dim,),
                input_var=obs_var,
                output_dim=action_dim,
                hidden_sizes=std_hidden_sizes,
                hidden_nonlinearity=std_hidden_nonlinearity,
                output_nonlinearity=None,
            ).output_layer
        else:
            l_log_std = ParamLayer(
                mean_network.input_layer,
                num_units=action_dim,
                param=lasagne.init.Constant(np.log(init_std)),
                name="output_log_std",
                trainable=learn_std,
            )

        mean_var, log_std_var = L.get_output([l_mean, l_log_std])

        self._l_mean = l_mean
        self._l_log_std = l_log_std

        self._dist = DiagonalGaussian()

        LasagnePowered.__init__(self, [l_mean, l_log_std])
        super(GaussianMLPPolicy_snn, self).__init__(env_spec)

        self._f_dist = ext.compile_function(
            inputs=[obs_var],
            outputs=[mean_var, log_std_var],
        )

    ##CF 
    @property
    def latent_space(self):
        return Box(low= -np.inf, high=np.inf, shape=(1,))
    ##
    
    ##CF - the mean and var now also depend on the particular latent sampled
    def dist_info_sym(self, obs_var, latent_var, action_var):
        #generate the generalized input (append latent to obs.)
        extended_obs_var = TT.concatenate( [obs_var,latent_var], axis=1 )
        mean_var, log_std_var = L.get_output([self._l_mean, self._l_log_std], extended_obs_var)
        return dict(mean=mean_var, log_std=log_std_var)
    ##
    # def dist_info_sym(self, obs_var, action_var):
    #     mean_var, log_std_var = L.get_output([self._l_mean, self._l_log_std], obs_var)
    #     return dict(mean=mean_var, log_std=log_std_var)

    @overrides
    def get_action(self, observation):
        ##CF
        if self.latent_type=='normal':
            latent = np.random.randn(self.latent_dim,)  
        elif self.latent_type=='binomial':
            latent = np.random.binomial(4,0.5,(self.latent_dim,))
        extended_obs = np.concatenate( (observation,latent) )
        #make mean, log_std also depend on the latent (as observ.)
        mean, log_std = [x[0] for x in self._f_dist([extended_obs])]
        rnd = np.random.randn(len(mean))
        action = rnd * np.exp(log_std) + mean
        return action, dict(mean=mean, log_std=log_std, latent=latent)

    def log_diagnostics(self, paths):
        log_stds = np.vstack([path["agent_infos"]["log_std"] for path in paths])
        logger.record_tabular('AveragePolicyStd', np.mean(np.exp(log_stds)))

    @property
    def distribution(self):
        return self._dist