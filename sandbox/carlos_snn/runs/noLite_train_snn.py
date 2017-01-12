from rllab.sampler import parallel_sampler
parallel_sampler.initialize(n_parallel=2)
parallel_sampler.set_seed(1)

from rllab.baselines.linear_feature_baseline import LinearFeatureBaseline
from sandbox.carlos_snn.hallucinators.prior_hallucinator import PriorHallucinator
from sandbox.carlos_snn.policies.snn_mlp_policy import GaussianMLPPolicy_snn
from sandbox.carlos_snn.algos.trpo_snn import TRPO_snn
from sandbox.carlos_snn.regressors.latent_regressor import Latent_regressor

# new things
from sandbox.carlos_snn.bonus_evaluators.grid_bonus_evaluator import GridBonusEvaluator

# from rllab.envs.mujoco.swimmer_env import SwimmerEnv
# from rllab.envs.mujoco.humanoid_env import HumanoidEnv
from sandbox.carlos_snn.envs.mujoco.snake_env import SnakeEnv

from rllab.envs.normalized_env import normalize

# stub(globals())

# env = HalfCheetahEnv()  # GymEnv('HalfCheetah-v1', record_video=False)
# env = normalize(SwimmerEnv())
# env = normalize(HumanoidEnv())
# env = normalize(SimpleHumanoidEnv())
env = normalize(SnakeEnv(ego_obs=True))

mesh_density = 5

for reward_coef in [0]:
    for latent_dim in [6]:
        for latent_name in ['categorical']:
            for n_samples in [0]:
                for noisify_coef in [0.1]:
                    for snn_H_bonus in [0, 0.001, 0.1, 1]:
                        policy = GaussianMLPPolicy_snn(
                            env_spec=env.spec,
                            latent_dim=latent_dim,
                            latent_name=latent_name,
                            bilinear_integration=True,  # concatenate also the outer product
                            hidden_sizes=(32, 32),  # (100, 50, 25),
                            min_std=1e-6,
                        )

                        baseline = LinearFeatureBaseline(env_spec=env.spec)

                        if latent_dim:
                            latent_regressor = Latent_regressor(
                                env_spec=env.spec,
                                policy=policy,
                                predict_all=True,  # use all the predictions and not only the last
                                obs_regressed='all',  # [-3] is the x-position of the com, otherwise put 'all'
                                act_regressed=[],  # use [] for nothing or 'all' for all.
                                use_only_sign=False,  # for the regressor we use only the sign to estimate the post
                                noisify_traj_coef=noisify_coef,
                                optimizer=None,  # this defaults to LBFGS, for first order, put 'fist_order'
                                regressor_args={
                                    'hidden_sizes': (32, 32),  # (100, 50, 25),
                                    'name': 'latent_reg',
                                    'use_trust_region': True,  # this is useless if using 'first_order'
                                }
                            )
                        else:
                            latent_regressor = None

                        bonus_evaluators = [GridBonusEvaluator(mesh_density=mesh_density, snn_H_bonus=snn_H_bonus)]
                        reward_coef_bonus = [1]

                        algo = TRPO_snn(
                            env=env,
                            policy=policy,
                            baseline=baseline,
                            self_normalize=True,
                            log_individual_latents=True,  # this will log the progress of every latent value!
                            log_deterministic=True,
                            logged_MI=[dict(recurrent=False,  #it will copy all but this (if other to copy,
                                            obs_regressed=[-3],         # code changes in npo_snn... to do)
                                            act_regressed=[],
                                            )
                                       ],  # for none use empty list [], for all use 'all_individual',
                                           # otherwise list of pairs, each entry a list of numbers ([obs],[acts])
                                            #### this sets a RECURRENT ONE!!
                            hallucinator=PriorHallucinator(env_spec=env.spec, policy=policy,
                                                           n_hallucinate_samples=n_samples),
                            latent_regressor=latent_regressor,
                            reward_coef=reward_coef,
                            bonus_evaluator=bonus_evaluators,
                            # switch_lat_every=100,
                            reward_coef_bonus=reward_coef_bonus,
                            batch_size=50000,
                            whole_paths=True,
                            max_path_length=500,
                            n_itr=500,
                            discount=0.99,
                            step_size=0.01,
                        )

                        for s in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
                            exp_prefix = 'egoSnake64-snn'
                            exp_name = exp_prefix + '_{}MI_{}grid_{}lat_{}_bil_{:04d}'.format(
                                ''.join(str(snn_H_bonus).split('.')), mesh_density,
                                latent_dim, latent_name, s)
                            # run_experiment_lite(
                            #     stub_method_call=algo.train(),
                            #     mode='local',
                            #     # Number of parallel workers for sampling
                            #     n_parallel=2,
                            #     # Only keep the snapshot parameters for the last iteration
                            #     snapshot_mode="last",
                            #     # Specifies the seed for the experiment. If this is not provided, a random seed
                            #     # will be used
                            #     seed=s,
                            #     # plot=True,
                            #     # Save to data/ec2/exp_prefix/exp_name/
                            #     exp_prefix=exp_prefix,
                            #     exp_name=exp_name,
                            #     sync_s3_pkl=True,  # for sync the pkl file also during the training
                            #     sync_s3_png=True,
                            #     terminate_machine=True,  # dangerous to have False!
                            # )
                            algo.train()
