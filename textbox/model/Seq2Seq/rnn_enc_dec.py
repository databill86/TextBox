# @Time   : 2020/11/14
# @Author : Junyi Li
# @Email  : lijunyi@ruc.edu.cn


import torch
import torch.nn as nn
import torch.nn.functional as F

from textbox.utils import InputType
from textbox.model.abstract_generator import ConditionalGenerator
from textbox.module.Encoder.rnn_encoder import BasicRNNEncoder
from textbox.module.Decoder.rnn_decoder import BasicRNNDecoder, AttentionalRNNDecoder
from textbox.model.init import xavier_normal_initialization


class RNNEncDec(ConditionalGenerator):
    r"""BPR is a basic matrix factorization model that be trained in the pairwise way.

    """
    input_type = InputType.NOISE

    def __init__(self, config, dataset):
        super(RNNEncDec, self).__init__(config, dataset)

        # load parameters info
        self.embedding_size = config['embedding_size']
        self.hidden_size = config['hidden_size']
        self.num_layers = config['num_layers']
        self.rnn_type = config['rnn_type']
        self.bidirectional = config['bidirectional']
        self.combine_method = config['combine_method']

        self.padding_token_idx = dataset.padding_token_idx
        self.sos_token_idx = dataset.sos_token_idx
        self.eos_token_idx = dataset.eos_token_idx

        # define layers and loss
        self.token_embedder = nn.Embedding(self.vocab_size, self.embedding_size, padding_idx=self.padding_token_idx)

        self.encoder = BasicRNNEncoder(self.embedding_size, self.hidden_size, self.num_layers, self.rnn_type,
                                       self.bidirectional, self.combine_method)
        self.decoder = BasicRNNDecoder(self.embedding_size, self.hidden_size, self.num_layers, self.rnn_type)

        self.vocab_linear = nn.Linear(self.hidden_size, self.vocab_size)
        self.loss = nn.CrossEntropyLoss(ignore_index=self.padding_token_idx)

        # parameters initialization
        self.apply(xavier_normal_initialization)

    def generate(self, eval_data):
        generate_corpus = []
        number_to_gen = 10
        idx2token = eval_data.idx2token
        for _ in range(number_to_gen):
            hidden_states = torch.zeros(self.num_layers, 1, self.hidden_size).to(self.device)
            generate_tokens = []
            input_seq = torch.LongTensor([[self.sos_token_idx]]).to(self.device)
            for gen_idx in range(100):
                decoder_input = self.token_embedder(input_seq)
                outputs, hidden_states = self.decoder(hidden_states, decoder_input)
                token_logits = self.vocab_linear(outputs)
                topv, topi = torch.log(F.softmax(token_logits, dim=-1) + 1e-12).data.topk(k=4)
                topi = topi.squeeze()
                token_idx = topi[0].item()
                if token_idx == self.eos_token_idx or gen_idx >= 100:
                    break
                else:
                    generate_tokens.append(idx2token[token_idx])
                    input_seq = torch.LongTensor([[token_idx]]).to(self.device)
            generate_corpus.append(generate_tokens)
        return generate_corpus

    def calculate_loss(self, corpus, epoch_idx=0):
        source_text = corpus['source_text']
        source_length = corpus['source_text_length']

        input_text = corpus['target_text'][:, :-1]
        target_text = corpus['target_text'][:, 1:]

        source_embeddings = self.token_embedder(source_text)
        input_embeddings = self.token_embedder(input_text)

        encoder_outputs, enc_final_states = self.encoder(source_embeddings, source_length)
        decoder_outputs, hidden_states = self.decoder(input_embeddings, enc_final_states)

        token_logits = self.vocab_linear(decoder_outputs)
        token_logits = token_logits.view(-1, token_logits.size(-1))
        target_text = target_text.contiguous().view(-1)

        loss = self.loss(token_logits, target_text)
        return loss