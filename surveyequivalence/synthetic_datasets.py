from surveyequivalence import DiscreteLabelsWithNoise, DiscreteState, Prediction, DiscreteDistributionPrediction
from typing import Sequence, Dict
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib
import os
from datetime import datetime


############ Mock Classifier ###############

class MockClassifier:
    """A mock classifier has access to each item's state when generating a prediction,
    something that a real classifier would not have access to"""
    def __init__(self,
                 name,
                 label_predictors: Dict[str, Prediction],
                 # pos_state_predictor: Sequence[float],
                 # neg_state_predictor: Sequence[float],
                 ):
        self.name = name
        self.label_predictors = label_predictors

    def make_predictions(self, item_states):
        # def classifier_item_state(state):
        #     if state.state_name == 'pos':
        #         return self.pos_state_predictor
        #     else:
        #         return self.neg_state_predictor
        
        return [self.label_predictors[s.state_name] for s in item_states]


############ Synthetic Dataset Generator ###############

class SyntheticDatasetGenerator:
    def __init__(self,
                 expert_state_generator,
                 num_items_per_dataset = 1000,
                 num_labels_per_item=10,
                 mock_classifiers=None,
                 name=''):
        self.expert_state_generator = expert_state_generator
        self.num_items_per_dataset = num_items_per_dataset
        self.num_labels_per_item = num_labels_per_item
        self.name = name
        # make a private empty list, not a shared default empty list if mock_classifiers not specified
        self.mock_classifiers = mock_classifiers if mock_classifiers else []

        self.expert_item_states = expert_state_generator.draw_states(num_items_per_dataset)

    def generate_labels(self, item_states, num_labels_per_item=None, rater_prefix="e"):
        if not num_labels_per_item:
            num_labels_per_item = self.num_labels_per_item
        return pd.DataFrame(
            [state.draw_labels(self.num_labels_per_item) for state in item_states],
            columns=[f"{rater_prefix}_{i}" for i in range(1, self.num_labels_per_item + 1)]
        )


class SyntheticBinaryDatasetGenerator(SyntheticDatasetGenerator):
    def __init__(self, expert_state_generator, num_items_per_dataset = 1000, num_labels_per_item=10,
                 mock_classifiers=None, name=None,
                 amateur_noise_multiplier=None, k_amateurs_per_label=1):
        super().__init__(expert_state_generator, num_items_per_dataset, num_labels_per_item, mock_classifiers, name)

        self.k_amateurs_per_label=k_amateurs_per_label
        if amateur_noise_multiplier:
            self.amateur_item_states = self.make_noisier_binary_states(amateur_noise_multiplier)
        else:
            self.amateur_item_states = None

    def make_noisier_binary_states(self, noise_multiplier):

        def make_noisier_state(state, multiplier):
            pr_pos, pr_neg = state.probabilities
            if pr_pos >= .5:
                new_pr_pos = pr_pos / multiplier

            else:
                new_pr_pos = pr_pos * multiplier
            new_pr_neg = 1 - new_pr_pos

            return DiscreteState(state_name=state.state_name,
                                 labels=state.labels,
                                 probabilities=[new_pr_pos, new_pr_neg])

        unique_states = list(set(self.expert_item_states))
        d = {s: make_noisier_state(s, noise_multiplier) for s in unique_states}

        return np.array([d[s] for s in self.expert_item_states])

    def plot_item_state_distribution(self):
        # called if you are making a standalone graph; for insets, .make_histogram is called directly

        # make Figure and axes objects
        fig, ax = plt.subplots()

        fig.set_size_inches(18.5, 10.5)

        # add histogram
        self.make_histogram(ax)

        # save figure
        if not os.path.isdir('plots'):
            os.mkdir('plots')
        fig.savefig(f'plots/{self.name} {datetime.now().strftime("%d-%m-%Y_%I-%M-%S_%p")}.png')

        pass

    def make_histogram(self, ax):
        ax.set_xlabel('State')
        ax.set_ylabel('Frequency')
        ax.set(xlim=(0,1))
        ax.hist([s.probabilities[0] for s in self.expert_item_states],
                25,
                align='right')
        # ax.set_yticks([])
        # ax.set_xticks([])

class Dataset():
    def __init__(self, dataset, amateur_dataset, classifiers):
        self.dataset=dataset
        self.amateur_dataset=amateur_dataset
        self.classifiers=classifiers

    def compute_classifier_scores(self, scorer):
        ##TODO: score against random rater from dataset; take mean over many sample
        ##Currently just scores against first column, r1
        def score_against_random_rater(col):
            return scorer.score(col, self.dataset['r1'])

        return self.classifier_predictions.apply(score_against_random_rater, axis=0)

class SyntheticDataset(Dataset):
    def __init__(self, ds_generator):
        self.ds_generator=ds_generator

        self.set_datasets()

    def set_datasets(self):
        ds_generator=self.ds_generator

        # create the expert dataset
        self.dataset = ds_generator.generate_labels(ds_generator.expert_item_states)

        # create the amateur dataset if applicable
        if ds_generator.amateur_item_states is not None:
            amateur_dataset = ds_generator.generate_labels(ds_generator.amateur_item_states,
                                              num_labels_per_item=ds_generator.num_labels_per_item * ds_generator.k_amateurs_per_label,
                                                           rater_prefix='a')
            if ds_generator.k_amateurs_per_label > 1:
                # get a group of k amateur labelers and take their majority label as the actual label
                majority_winners = stats.mode(amateur_dataset.reshape(-1, k_amateurs_per_label))
                print(majority_winners)
                foobar # this code hasn't been tested yet, so break if someone tries using it
                self.amateur_dataset = stats.mode(amateur_dataset.reshape(-1, k_amateurs_per_label)).mode
            else:
                self.amateur_dataset = amateur_dataset

        # create the classifier predictions for any mock classifiers
        self.classifier_predictions = pd.DataFrame({mc.name : mc.make_predictions(ds_generator.expert_item_states)
                                                    for mc in ds_generator.mock_classifiers})

def make_perceive_with_noise_datasets():

    def make_perceive_with_noise_datasets(epsilon):
        pos_state_probabilities = [1 - epsilon, epsilon]
        neg_state_probabilities = [.05 + epsilon, .95 - epsilon]
        expert_state_generator = \
            DiscreteLabelsWithNoise(states=[DiscreteState(state_name='pos',
                                                          labels=['pos', 'neg'],
                                                          probabilities=pos_state_probabilities),
                                            DiscreteState(state_name='neg',
                                                          labels=['pos', 'neg'],
                                                          probabilities=neg_state_probabilities)
                                            ],
                                    probabilities=[.8, .2]
                                    )

        dsg = SyntheticBinaryDatasetGenerator(expert_state_generator=expert_state_generator,
                                              name=f'80% {pos_state_probabilities}; 20% {neg_state_probabilities}'
                                              )

        dsg.mock_classifiers.append(MockClassifier(
            name='h_infinity',
            label_predictors={
                'pos': DiscreteDistributionPrediction(['pos', 'neg'], pos_state_probabilities),
                'neg': DiscreteDistributionPrediction(['pos', 'neg'], neg_state_probabilities)
            }))

        return SyntheticDataset(dsg)

    return [make_perceive_with_noise_datasets(pct/100) for pct in range(2, 42, 4)]



def make_discrete_dataset_1():
    expert_state_generator = \
        DiscreteLabelsWithNoise(states=[DiscreteState(state_name='pos',
                                                          labels=['pos', 'neg'],
                                                          probabilities=[.9, .1]),
                                        DiscreteState(state_name='neg',
                                                          labels=['pos', 'neg'],
                                                          probabilities=[.25, .75])
                                        ],
                                probabilities=[.8, .2]
                                )

    dsg = SyntheticBinaryDatasetGenerator(expert_state_generator= expert_state_generator,
                                amateur_noise_multiplier=1.1,
                                name='dataset 1: 80% 90-10; 20% 25-75',
                                )

    # dsg.mock_classifiers.append(MockClassifier(
    #     name='.95 .2',
    #     label_predictors={
    #         'pos': DiscreteDistributionPrediction(['pos', 'neg'], [.95, .05]),
    #         'neg': DiscreteDistributionPrediction(['pos', 'neg'], [.2, .8])
    #     }))
    #
    # dsg.mock_classifiers.append(MockClassifier(
    #     name='.92 .24',
    #     label_predictors={
    #         'pos': DiscreteDistributionPrediction(['pos', 'neg'], [.92, .08]),
    #         'neg': DiscreteDistributionPrediction(['pos', 'neg'], [.24, .76])
    #     }))

    dsg.mock_classifiers.append(MockClassifier(
        name='h_infinity',
        label_predictors={
            'pos': DiscreteDistributionPrediction(['pos', 'neg'], [.9, .1]),
            'neg': DiscreteDistributionPrediction(['pos', 'neg'], [.25, .75])
        }))

    return SyntheticDataset(dsg)


def make_discrete_dataset_2():
    expert_state_generator = \
        DiscreteLabelsWithNoise(states=[DiscreteState(state_name='pos',
                                                      labels=['pos', 'neg'],
                                                      probabilities=[.5, .5]),
                                        DiscreteState(state_name='neg',
                                                      labels=['pos', 'neg'],
                                                      probabilities=[.3, .7])
                                        ],
                                probabilities=[.5, .5]
                                )

    dsg = SyntheticBinaryDatasetGenerator(expert_state_generator= expert_state_generator)
    return SyntheticDataset(dsg)


def make_discrete_dataset_3():
    expert_state_generator = \
        DiscreteLabelsWithNoise(states=[DiscreteState(state_name='pos',
                                                      labels=['pos', 'neg'],
                                                      probabilities=[.4, .6]),
                                        DiscreteState(state_name='neg',
                                                      labels=['pos', 'neg'],
                                                      probabilities=[.7, .3])
                                        ],
                                probabilities=[.4, .6]
                                )

    dsg = SyntheticBinaryDatasetGenerator(expert_state_generator= expert_state_generator)
    return SyntheticDataset(dsg)