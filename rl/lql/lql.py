from timeit import default_timer as timer
import pickle
import gymnasium as gym
import numpy as np
from feature_transformer import FeatureTransformer
from taxi_feature_extractor import TaxiFeatureExtractor

feature_extractors_dict = {
  "Taxi-v3": TaxiFeatureExtractor
}

class QLearningAgentLinear:

  def __init__(self, 
               env, 
               decay_rate, 
               learning_rate, 
               gamma):
    self.env = env
    env_name = env.unwrapped.spec.id
    self.fex = feature_extractors_dict[env_name](env)
    self.w = np.random.rand(self.fex.get_num_features())
    
    self.epsilon = 1.0
    self.max_epsilon = 1.0
    self.min_epsilon = 0.01
    self.decay_rate = decay_rate
    self.learning_rate = learning_rate
    self.gamma = gamma 
    self.epsilons_ = []

  def choose_action(self, state, is_in_exploration_mode = True):
    exploration_tradeoff = np.random.uniform(0, 1)
    if is_in_exploration_mode and exploration_tradeoff < self.epsilon:
      # exploration
      action = self.env.action_space.sample()    
    else:
      action = self.policy(state)
    return action

  def policy(self, state):
    # exploitation (taking the biggest Q value for this state)
    return self.__get_action_and_value(state)[0]

  def get_value(self, state):
    return self.__get_action_and_value(state)[1]

  def get_qvalues(self, state):
    q_values = {}
    for action in range(self.env.action_space.n):
      q_values[action]  = self.get_qvalue(state, action)
    return q_values

  def get_features_as_array(self, state, action):
    feature_vector = self.fex.get_features(state, action)
    feature_vector = feature_vector.reshape(1, -1)
    feature_vector = feature_vector.flatten()    
    # constant feature corresponding to the bias term
    feature_vector[0] = 1.0

    return feature_vector
    
  def get_qvalue(self, state, action):
    features = self.get_features_as_array(state, action)
    return np.dot(self.w, features)

  def __get_action_and_value(self, state):
    max_qvalue = float("-inf")
    best_action = 0
    for action in range(self.env.action_space.n):
      q_value  = self.get_qvalue(state, action)
      if q_value > max_qvalue:
        max_qvalue = q_value
        best_action = action
    return [best_action, max_qvalue]

  def update(self, state, action, reward, next_state):
    # print('Weights before:', self.get_weights())
    difference = (reward + (self.gamma * self.get_value(next_state))) - self.get_qvalue(state, action)
    # print('Q(s,a):', self.get_qvalue(state, action))
    # print('max Q(s,a):', self.get_value(next_state))
    # print('reward:', reward)
    # print('difference:', difference)
    if difference < -100:
       difference = -100
    if difference > 100:
       difference = 100
    features = self.ftrans.get_features_as_array(state, action)
    self.w = self.w + self.learning_rate * difference * features

  def train(self, num_episodes: int):

    successful_episodes = 0

    rewards_per_episode = []
    penalties_per_episode = []

    start_time = timer()  # Record the start time

    for episode in range(num_episodes):
      terminated = False
      truncated = False

      state, _ = self.env.reset()

      total_rewards = 0
      steps = 0

      total_penalties = 0

      while not (terminated or truncated):
        steps += 1
        action = self.choose_action(state)
        new_state, reward, terminated, truncated, _ = self.env.step(action)

        if reward == -10:
            total_penalties += 1

        self.update(state, action, reward, new_state)
        total_rewards += reward

        assert not np.isnan(self.get_weights()).any()
        assert not (any(self.get_weights() > 1e6)), f"Weigths explosion: {self.get_weights()}"

        if (terminated or truncated):
          # Reduce epsilon to decrease the exploration over time
          self.epsilon = self.min_epsilon + (self.max_epsilon - self.min_epsilon) * \
            np.exp(-self.decay_rate * episode)
          self.epsilons_.append(self.epsilon)
          if terminated:
            successful_episodes += 1
        
        state = new_state

      rewards_per_episode.append(total_rewards)
      penalties_per_episode.append(total_penalties)

      if episode % 50 == 0:
        end_time = timer()  # Record the end time
        execution_time = end_time - start_time
        print("Episode# %d/%d (%d successful)" % (episode+1, num_episodes, successful_episodes))
        print(f"\tElapsed time = {execution_time:.2f}s")
        print("\tTotal rewards %d" % total_rewards)
        print("\tTotal steps: %d" % steps)
        print("\tCurrent epsilon: %.4f" % self.epsilon)
        print("\tTotal penalties: %d" % total_penalties)
        print("\tw:", self.w)
        # print("\tCurrent weights: %s" % self.get_weights())
        print()

    return penalties_per_episode, rewards_per_episode

  def get_weights(self):
    return self.w

  def save(self, filename):
    # open a file, where you ant to store the data
    file = open(filename, 'wb')

    # dump information to that file
    pickle.dump(self, file)

    # close the file
    file.close()

  @staticmethod
  def load_agent(filename):
    # open a file, where you stored the pickled data
    file = open(filename, 'rb')

    # dump information to that file
    agent = pickle.load(file)

    return agent