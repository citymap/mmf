import copy

from collections import deque
from collections import namedtuple

from tensorflow import keras

from agent.deepq import *
from env.log import Logger

BUFFER_SIZE = 20000


class Experience:
    def __init__(self, state, action, reward, next_state, done, estimats, q_values=None):
        self.state = state
        self.action= action
        self.reward= reward
        self.next_state= next_state
        self.done = done
        self.estimates = estimats
        self.q_values = q_values

class HP:
    NETWORK_UPDATE_CYCLE = 2

    def __init__(self):
        pass


class Agent(BaseAgent):
    global_brain = None

    def __init__(self):
        super(Agent, self).__init__()
        if Agent.global_brain is None:
            Agent.global_brain = self.create_brain()
        self.local_brain = self.create_brain()
        self.copy_brain_to_local()


    def create_brain(self):
        l_input = keras.layers.Input(shape=(NUMBER_OF_LAYERS, BOARD_TIME_WIDTH, BOARD_WIDTH))
        conv2d = keras.layers.Conv2D(32, (4, 4), activation='relu', padding='same')(l_input)
        conv2d = keras.layers.Conv2D(64, (2, 2), activation='relu', padding='same')(conv2d)
        conv2d = keras.layers.Conv2D(64, (1, 1), activation='relu', padding='same')(conv2d)
        flat_view = keras.layers.Flatten()(conv2d)

        margin_input = keras.layers.Input(shape=(2,))

        marge_out = keras.layers.concatenate([flat_view, margin_input])

        fltn = keras.layers.Dense(512, activation='relu')(marge_out)

        v = keras.layers.Dense(units=256, activation='relu')(fltn)
        v = keras.layers.Dense(1)(v)
        adv = keras.layers.Dense(256, activation='relu')(fltn)
        adv = keras.layers.Dense(self.number_of_actions)(adv)
        y = keras.layers.concatenate([v, adv])
        #        l_output = keras.layers.Dense(self.number_of_actions)(y)
        l_output = keras.layers.Lambda(
        lambda a: keras.backend.expand_dims(a[:, 0], -1) + a[:, 1:] - tf.stop_gradient(
            keras.backend.mean(a[:, 1:], keepdims=True)),
        output_shape=(self.number_of_actions,))(y)
        model = keras.Model([l_input, margin_input], l_output)

        model.summary()

        model.compile(loss='mse', optimizer='adam')

        return model

    def copy_brain_to_local(self):
        self.local_brain.set_weights(self.global_brain.get_weights())

    def estimate(self, status):
        return self.predict(status)

    def predict(self, s, use_global_brain = False):
        brain = None

        if use_global_brain:
            brain = self.global_brain
        else:
            brain = self.local_brain

        e = brain.predict([np.expand_dims(s.board, axis=0), np.expand_dims(s.rewards, axis=0)])[0]

        return e


class Trainer():
    def __init__(self, env, agent, gamma=0.99, buffer_size=BUFFER_SIZE):
        self.buffer_size = buffer_size
        self.local_buffer = deque(maxlen=self.buffer_size)
        self.reward = 0
        self.start_time = 0
        self.end_time = 0
        self.loss = None
        self.total_reward = 0
        self.duration = 0
        self.logger = Logger()

        self.env = env
        self.agent = agent
        self.gamma = gamma

    def experience_generator(self):
        while True:
            state = self.env.reset()

            while True:
                action = self.agent.policy(state)
                n_state, reward, done, info = self.env.step(action)

                yield state, n_state, action, reward, done, info

                if done:
                    break

                state = n_state

    def create_generator(self):
        generator = self.experience_generator()

        return generator

    def compute_priority(self):
        pass

    def add_replay_buffer(self):
        pass


    def calc_multi_step_q_value(self, start_index, steps, gamma=0.99):
        '''
        calc q value in reverse order.
            [t][t-1][t-2][t-3]......
        :param start_index:
        :param steps:
        :return:
        '''
        index = len(self.local_buffer)

        reward = 0
        while not index:
            index -= 1

            experience = self.local_buffer[start_index + index]
            if experience.done:
                reward += gamma * experience.reward
                break

            if index == 1:
                reward += gamma * np.argmax(experience.estimates)
                break

            reward += gamma * experience.estimates[experience.action]


        experience = self.local_buffer[start_index]
        action = experience.action

        self.local_buffer[start_index].q_values[action] = reward


    def predict_q_values(self, status):
        e = self.agent.predict(status)

        if status.is_able_to_buy():
            e[ACTION.BUY_NOW] = status.get_buy_now_reward()
        else:
            e[ACTION.BUY_NOW] = 0
            e[ACTION.BUY] = 0

        if status.is_able_to_sell():
            e[ACTION.SELL_NOW] = status.get_sell_now_reward()
        else:
            e[ACTION.SELL_NOW] = 0
            e[ACTION.SELL] = 0

        return e


    def one_episode(self):
        # Obtain latest network parameters
        # Initialize Environment
        generator = self.create_generator()

        for state, n_state, action, reward, done, info in generator:
            estimate = self.predict_q_values(state)
            self.local_buffer.append(Experience(state, action, reward, n_state, done, estimate, copy.copy(estimate)))
            if done:
                break


if __name__ == '__main__':
    env = Trade()
    agent = BaseAgent()

    trainer = Trainer(env, agent)

    trainer.one_episode()


