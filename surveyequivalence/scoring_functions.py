from abc import ABC, abstractmethod
from typing import Sequence, Dict
import numpy as np
from .predictors import Prediction


class Score(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def agreement_score(self, classifier_predictions: Sequence[Prediction],
                    rater_labels):
        pass

""" 
Forgive me, Paul
"""
class Agreement(Score):
    def __init__(self):
        super().__init__()

    def agreement_score(self, classifier_predictions: Sequence[Prediction],
                        rater_labels):
        """
        Resolve predictions to identify the most likely single label;
        Return the fraction where predicted matches actual

        >>> self.agreement_score(['a', 'b'], [[.3, .7], [.4, .6], [.6, .4]], ['b', 'b', 'b'])
        0.6666666666666666

        >>> self.agreement_score(['a', 'b'], [[.3, .7], [.4, .6], [.6, .4]], ['a', 'b', 'b'])
        0.3333333333333333
        """
        classifier_labels = [pred.value for pred in classifier_predictions]
        return np.mean([a == b for (a, b) in zip([p.value for p in classifier_predictions],
                                                 rater_labels)])
