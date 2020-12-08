# @Time   : 2020/11/16
# @Author : Junyi Li
# @Email  : lijunyi@ruc.edu.cn


# UPDATE:
# @Time   : 2020/12/04
# @Author : Gaole He
# @Email  : hegaole@ruc.edu.cn

import os
import nltk
import collections
import random
import numpy as np
from logging import getLogger
from textbox.data.dataset import Dataset


class PairedSentenceDataset(Dataset):
    def __init__(self, config, saved_dataset=None):
        self.source_language = config['source_language'].lower()
        self.target_language = config['target_language'].lower()
        self.source_suffix = config['source_suffix']
        self.target_suffix = config['target_suffix']
        if config['target_max_vocab_size'] is None or config['source_max_vocab_size'] is None:
            self.source_max_vocab_size = config['max_vocab_size']
            self.target_max_vocab_size = config['max_vocab_size']
        else:
            self.source_max_vocab_size = config['source_max_vocab_size']
            self.target_max_vocab_size = config['target_max_vocab_size']

        if config['target_max_seq_length'] is None or config['source_max_seq_length'] is None:
            self.source_max_vocab_size = config['max_seq_length']
            self.target_max_vocab_size = config['max_seq_length']
        else:
            self.source_max_seq_length = config['source_max_seq_length']
            self.target_max_seq_length = config['target_max_seq_length']
        super().__init__(config, saved_dataset)

    def _get_preset(self):
        """Initialization useful inside attributes.
        """
        self.source_token2idx = {}
        self.source_idx2token = {}
        self.target_token2idx = {}
        self.target_idx2token = {}
        self.source_text_data = []
        self.target_text_data = []

    def __len__(self):
        return sum([len(data) for data in self.source_text_data])

    def _load_data(self, dataset_path):
        """Load features.
        Firstly load interaction features, then user/item features optionally,
        finally load additional features if ``config['additional_feat_suffix']`` is set.
        Args:
            dataset_name (str): dataset name.
            dataset_path (str): path of dataset dir.
        """
        train_src_file = os.path.join(dataset_path, 'train.' + self.source_suffix)
        if not os.path.isfile(train_src_file):
            raise ValueError('File {} not exist'.format(train_src_file))
        for prefix in ['train', 'dev', 'test']:
            source_file = os.path.join(dataset_path, '{}.{}'.format(prefix, self.source_suffix))
            source_text = []
            fin = open(source_file, "r")
            for line in fin:
                words = nltk.word_tokenize(line.strip(), language=self.source_language)[:self.source_max_seq_length]
                source_text.append(words)
            fin.close()
            self.source_text_data.append(source_text)

            target_file = os.path.join(dataset_path, '{}.{}'.format(prefix, self.target_suffix))
            target_text = []
            fin = open(target_file, "r")
            for line in fin:
                words = nltk.word_tokenize(line.strip(), language=self.target_language)[:self.target_max_seq_length]
                target_text.append(words)
            fin.close()
            self.target_text_data.append(target_text)

    def _data_processing(self):
        self._build_vocab()

    def _build_vocab_text(self, text_data_list, max_vocab_size):
        word_list = list()
        for text_data in text_data_list:
            for text in text_data:
                word_list.extend(text)
        tokens = [token for token, _ in collections.Counter(word_list).items()]
        tokens = [self.padding_token, self.unknown_token, self.sos_token, self.eos_token] + tokens
        tokens = tokens[:max_vocab_size]
        idx2token = dict(zip(range(max_vocab_size), tokens))
        token2idx = dict(zip(tokens, range(max_vocab_size)))
        return idx2token, token2idx

    def _build_vocab(self):
        self.source_idx2token, self.source_token2idx = self._build_vocab_text(self.source_text_data,
                                                                              max_vocab_size=self.source_max_vocab_size)
        self.target_idx2token, self.target_token2idx = self._build_vocab_text(self.target_text_data,
                                                                              max_vocab_size=self.target_max_vocab_size)
        print("Source vocab size: {}, Target vocab size: {}".format(len(self.source_idx2token),
                                                                    len(self.target_idx2token)))

    def shuffle(self):
        pass

    def build(self, eval_setting=None):
        """Processing dataset according to evaluation setting, including Group, Order and Split.
        See :class:`~textbox.config.eval_setting.EvalSetting` for details.

        Args:
            eval_setting (:class:`~textbox.config.eval_setting.EvalSetting`):
                Object contains evaluation settings, which guide the data processing procedure.

        Returns:
            list: List of builded :class:`Dataset`.
        """
        info_str = ''
        corpus_list = []
        for i, prefix in enumerate(['train', 'dev', 'test']):
            source_text_data = self.source_text_data[i]
            target_text_data = self.target_text_data[i]
            tp_data = {
                'source_idx2token': self.source_idx2token,
                'source_token2idx': self.source_token2idx,
                'source_text_data': source_text_data,
                'target_idx2token': self.target_idx2token,
                'target_token2idx': self.target_token2idx,
                'target_text_data': target_text_data
            }
            corpus_list.append(tp_data)
            if prefix == 'test':
                info_str += '{}: {} cases'.format(prefix, len(source_text_data))
            else:
                info_str += '{}: {} cases, '.format(prefix, len(source_text_data))
        self.logger.info(info_str)
        return corpus_list