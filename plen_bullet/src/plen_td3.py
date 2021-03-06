#!/usr/bin/env python

import numpy as np

from plen_ros_helpers.td3 import ReplayBuffer, TD3Agent, evaluate_policy

from plen_bullet import plen_env

import gym
import torch
import os

import time


def main():
    """ The main() function. """

    print("STARTING PLEN_TD3 NODE")

    # TRAINING PARAMETERS
    env_name = "PlenWalkEnv-v1"
    seed = 0
    max_timesteps = 4e6
    start_timesteps = 1e4  # 1e3 for testing purposes, use 1e4 for real
    expl_noise = 0.1
    batch_size = 100
    eval_freq = 1e4
    save_model = True
    file_name = "plen_walk_gazebo_"

    # Find abs path to this file
    my_path = os.path.abspath(os.path.dirname(__file__))
    results_path = os.path.join(my_path, "../results")
    models_path = os.path.join(my_path, "../models")

    if not os.path.exists(results_path):
        os.makedirs(results_path)

    if not os.path.exists(models_path):
        os.makedirs(models_path)

    env = gym.make(env_name, render=False)

    # Set seeds
    env.seed(seed)
    torch.manual_seed(seed)
    np.random.seed(seed)

    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = float(env.action_space.high[0])

    print("RECORDED MAX ACTION: {}".format(max_action))

    policy = TD3Agent(state_dim, action_dim, max_action)
    policy_num = 0
    if os.path.exists(models_path + "/" + "plen_walk_gazebo_" +
                      str(policy_num) + "_critic"):
        print("Loading Existing Policy")
        policy.load(models_path + "/" + "plen_walk_gazebo_" + str(policy_num))

    replay_buffer = ReplayBuffer()
    # Optionally load existing policy, replace 9999 with num
    buffer_number = 0  # BY DEFAULT WILL LOAD NOTHING, CHANGE THIS
    if os.path.exists(replay_buffer.buffer_path + "/" + "replay_buffer_" +
                      str(buffer_number) + '.data'):
        print("Loading Replay Buffer " + str(buffer_number))
        replay_buffer.load(buffer_number)
        # print(replay_buffer.storage)

    # Evaluate untrained policy and init list for storage
    evaluations = []

    state = env.reset()
    done = False
    episode_reward = 0
    episode_timesteps = 0
    episode_num = 0

    print("STARTED PLEN_TD3 NODE")

    for t in range(int(max_timesteps)):

        # time.sleep(1)

        episode_timesteps += 1

        # Select action randomly or according to policy
        # Random Action - no training yet, just storing in buffer
        if t < start_timesteps:
            action = env.action_space.sample()
            # rospy.logdebug("Sampled Action")
        else:
            # According to policy + Exploraton Noise
            # print("POLICY Action")
            """ Note we clip at +-0.99.... because Gazebo
                has problems executing actions at the
                position limit (breaks model)
            """
            action = np.clip(
                (policy.select_action(np.array(state)) + np.random.normal(
                    0, max_action * expl_noise, size=action_dim)),
                -max_action, max_action)
            # rospy.logdebug("Selected Acton: {}".format(action))

        # Perform action
        next_state, reward, done, _ = env.step(action)
        done_bool = float(
            done) if episode_timesteps < env._max_episode_steps else 0

        # Store data in replay buffer
        replay_buffer.add((state, action, next_state, reward, done_bool))

        state = next_state
        episode_reward += reward

        # Train agent after collecting sufficient data for buffer
        if t >= start_timesteps:
            policy.train(replay_buffer, batch_size)

        if done:
            # +1 to account for 0 indexing.
            # +0 on ep_timesteps since it will increment +1 even if done=True
            # print(
            #     "Total T: {} Episode Num: {} Episode T: {} Reward: {}".format(
            #         t + 1, episode_num, episode_timesteps, episode_reward))
            # Reset environment
            state, done = env.reset(), False
            evaluations.append(episode_reward)
            episode_reward = 0
            episode_timesteps = 0
            episode_num += 1

        # Evaluate episode
        if (t + 1) % eval_freq == 0:
            # evaluate_policy(policy, env_name, seed, 5, False)
            # THIS BREAKS THE ENVIRONMENT FOR SOME REASON...
            # # Reset environment
            # state, done = env.reset(), False
            # episode_reward = 0
            # episode_timesteps = 0
            # episode_num += 1

            # eval_reward = 0
            # while not done:
            #     action = policy.select_action(np.array(state))
            #     state, reward, done, _ = env.step(action)
            #     eval_reward += reward
            # evaluations.append(eval_reward)
            # print("---------------------------------------")
            # print("Evaluation Reward: {}".format(reward))
            # print("---------------------------------------")
            np.save(results_path + "/" + str(file_name), evaluations)
            if save_model:
                policy.save(models_path + "/" + str(file_name) + str(t))
                # replay_buffer.save(t)

    env.close()


if __name__ == '__main__':
    main()