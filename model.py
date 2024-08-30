# -*- coding: utf-8 -*-
"""transformer.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/16SZHlmhAtPVtERWNuaSZ3lMZpnP334uC
"""

import torch
from torch import nn
import math

class InputEmbedding(nn.Module):
  def __init__(self,d_model: int,vocab_size: int):
    super(InputEmbedding, self).__init__()
    self.d_model = d_model # dimension of input embedding
    self.vocab_size = vocab_size # max sequence length
    self.embedding_layer = nn.Embedding(self.vocab_size
                                        ,self.d_model)
  def forward(self,x):
    # (batch, seq_len) --> (batch, seq_len, d_model)

    # Multiply by sqrt(d_model) to scale
    # the embeddings according to the paper
    return self.embedding_layer(x) * math.sqrt(self.d_model)

class PositionalEncoding(nn.Module):
  def __init__(self,d_model:int,seq_len:int, dropout: float):
    super(PositionalEncoding, self).__init__()
    self.d_model = d_model
    self.seq_len = seq_len
    self.dropout = nn.Dropout(dropout)
    #Create a matrix of shape ()

    #Position vector: shape (seq_len,1)
    position_vector = torch.arange(0,seq_len,dtype = torch.float).unsqueeze(1) # (seq_len,1)

    #Div_term: shape (d_model)
    div_term_vector = torch.exp(torch.arange(0,d_model,2).float() * (-math.log(10000.0) / d_model))

    #PE vector: shape(seq_len,d_model)
    pe = torch.zeros(seq_len,d_model)

    #Sin vector: PE(pos,2i)
    pe[:,0::2] = torch.sin(position_vector * div_term_vector) # sin(position * (10000 ** (2i / d_model))

    #Cos vector: PE(pos,2i+1)
    pe[:,1::2] = torch.cos(position_vector * div_term_vector) # cos(position * (10000 ** (2i / d_model))

    #Add a batch dimension to positional encoding
    pe = pe.unsqueeze(0) # (1, seq_len, d_model)

    # Register the positional encoding as a buffer
    self.register_buffer('pe', pe)
  def forward(self, x):
    x = x + (self.pe[:,:x.shape[1],:]).requires_grad_(False) # (batch, seq_len, d_model)
    return self.dropout(x)
      
class LayerNormalization(nn.Module):
  def __init__(self, features: int, eps:float=10**-6):
    super(LayerNormalization,self).__init__()
    self.eps = eps
    #Learnable parameters (alpha , beta)
    self.alpha = nn.Parameter(torch.ones(features))
    self.beta = nn.Parameter(torch.zeros(features))
  def forward(self,x):
    # x (batch, seq_len, hidden_size)

    # Keep the dimension for broadcasting
    mean = x.mean(dim = -1, keepdim = True) # (batch, seq_len, 1)
    std = x.std(dim = -1, keepdim = True)   # (batch, seq_len, 1)

    # eps is to prevent dividing by zero or when std is very small
    return self.alpha * (x-mean) / (std + self.eps) + self.beta

class MultiHeadAttention(nn.Module):
  def __init__(self, d_model: int, num_heads: int, dropout: float):
    super(MultiHeadAttention,self).__init__()
    self.d_model = d_model
    self.num_heads = num_heads

    assert self.d_model % self.num_heads == 0

    self.d_k = self.d_model // self.num_heads # Dimension of vector seen by each head
    self.w_q = nn.Linear(d_model, d_model, bias=False) # Wq
    self.w_k = nn.Linear(d_model, d_model, bias=False) # Wk
    self.w_v = nn.Linear(d_model, d_model, bias=False) # Wv

    self.dropout = nn.Dropout(dropout)

    self.w_output = nn.Linear(d_model, d_model, bias=False) # w_output

  @staticmethod
  def attention(query,key,value,mask,dropout: nn.Dropout):
    d_k = query.shape[-1]

    #Q.T(K) - (batch, h, seq_len, d_k) --> (batch, h, seq_len, seq_len)
    attention_matrix = (query @ key.transpose(-2,-1)) / math.sqrt(d_k)

    if mask is not None:
      attention_matrix = attention_matrix.masked_fill(mask ==0, -1e10)

    #Apply softmax - (batch, h, seq_len, seq_len)
    attention_matrix = attention_matrix.softmax(dim=-1)

    if dropout is not None:
      attention_matrix = dropout(attention_matrix)

    # (batch, h, seq_len, seq_len) --> (batch, h, seq_len, d_k)
    return (attention_matrix @ value), attention_matrix

  def forward(self, q, k, v, mask):
    # (batch, seq_len, d_model) --> (batch, seq_len, d_model)
    query = self.w_q(q)
    key = self.w_k(k)
    value = self.w_v(v)

    # (batch, seq_len, d_model) --> (batch, seq_len, h, d_k) --> (batch, h, seq_len, d_k)
    query = query.view(query.shape[0], query.shape[1], self.num_heads, self.d_k).transpose(1, 2)
    key = key.view(key.shape[0], key.shape[1], self.num_heads, self.d_k).transpose(1, 2)
    value = value.view(value.shape[0], value.shape[1], self.num_heads, self.d_k).transpose(1, 2)

    #Calculate attention
    x, self.attention_matrix = MultiHeadAttention.attention(query,key,value,mask,self.dropout)

    # Combine all the heads together
    # (batch, h, seq_len, d_k) --> (batch, seq_len, h, d_k) --> (batch, seq_len, d_model)
    x = x.transpose(1,2).contiguous().view(x.shape[0],-1,self.num_heads * self.d_k)

    # Final linear layer
    # (batch, seq_len, d_model) --> (batch, seq_len, d_model)
    return self.w_output(x)

class ResidualConnection(nn.Module):
    def __init__(self, features: int, dropout: float):
      super(ResidualConnection,self).__init__()
      self.dropout = nn.Dropout(dropout)
      self.norm = LayerNormalization(features)

    def forward(self,x,sublayer):
      return x + self.dropout(sublayer(self.norm(x)))

"""
$$
FFN(x) = \max(0, xW_1 + b_1)W_2 + b_2
$$
"""

class FeedForward(nn.Module):
  def __init__(self, d_model: int, d_ff: int, dropout: float):
    super(FeedForward,self).__init__()
    self.linear_1 = nn.Linear(d_model,d_ff) #W1, b1
    self.dropout = nn.Dropout(dropout)
    self.linear_2 = nn.Linear(d_ff,d_model) #W2, b2

  def forward(self,x):
    # (batch, seq_len, d_model) --> (batch, seq_len, d_model) --> (batch, seq_len, d_model)
    return self.linear_2(self.dropout(torch.relu(self.linear_1(x))))

class EncoderBlock(nn.Module):
  def __init__(self, features: int, self_attention_block: MultiHeadAttention, feed_forward_block: FeedForward, dropout: float):
    super(EncoderBlock, self).__init__()
    self.self_attention_block = self_attention_block
    self.feed_forward_block = feed_forward_block
    self.residual_connections = nn.ModuleList([ResidualConnection(features, dropout) for _ in range(2)])

  def forward(self,x, src_mask):
    x = self.residual_connections[0](x, lambda x : self.self_attention_block(x,x,x,src_mask))
    x = self.residual_connections[1](x, self.feed_forward_block)
    return x

class Encoder(nn.Module):
  def __init__(self, features: int, layers: nn.ModuleList):
    super(Encoder,self).__init__()
    self.layers = layers
    self.norm = LayerNormalization(features)

  def forward(self, x, mask):
    for layer in self.layers:
      x = layer(x,mask)
    return self.norm(x)

class DecoderBlock(nn.Module):
  def __init__(self, features: int, mask_attention_block: MultiHeadAttention, encoder_decoder_attention_block: MultiHeadAttention, feed_forward_block: FeedForward, dropout: float):
    super(DecoderBlock, self).__init__()
    self.mask_attention_block = mask_attention_block
    self.encoder_decoder_attention_block = encoder_decoder_attention_block
    self.feed_forward_block = feed_forward_block
    self.residual_connections = nn.ModuleList([ResidualConnection(features,dropout) for _ in range(3)])

  def forward(self, x, encoder_output, src_mask, tgt_mask):
    x = self.residual_connections[0](x, lambda x : self.mask_attention_block(x,x,x,tgt_mask))
    x = self.residual_connections[1](x, lambda x : self.encoder_decoder_attention_block(x,encoder_output,encoder_output,src_mask))
    x = self.residual_connections[2](x, self.feed_forward_block)
    return x

class Decoder(nn.Module):
  def __init__(self, features: int, layers: nn.ModuleList):
    super(Decoder,self).__init__()
    self.layers = layers
    self.norm = LayerNormalization(features)

  def forward(self, x, encoder_output, src_mask, tgt_mask):
    for layer in self.layers:
      x = layer(x, encoder_output, src_mask, tgt_mask)
    return self.norm(x)

class ProjectionLayer(nn.Module):
  def __init__(self, d_model, vocab_size):
    super(ProjectionLayer, self).__init__()
    self.proj_layer = nn.Linear(d_model, vocab_size)

  def forward(self, x):
    # (batch, seq_len, d_model) --> (batch, seq_len, vocab_size)
    return self.proj_layer(x)

class Transformer(nn.Module):
  def __init__(self
               , encoder: Encoder
               , decoder: Decoder
               , src_embeddings: InputEmbedding
               , tgt_embeddings: InputEmbedding
               , src_pos: PositionalEncoding
               , tgt_pos: PositionalEncoding
               , projection_layer: ProjectionLayer):
    super(Transformer, self).__init__()
    self.encoder = encoder
    self.decoder = decoder
    self.src_embeddings = src_embeddings
    self.tgt_embeddings = tgt_embeddings
    self.src_pos = src_pos
    self.tgt_pos = tgt_pos
    self.projection_layer = projection_layer

  def encode(self, src: torch.Tensor, src_mask: torch.Tensor):
    src = self.src_embeddings(src)
    src = self.src_pos(src)
    return self.encoder(src, src_mask)

  def decode(self, encoder_output: torch.Tensor, src_mask: torch.Tensor, tgt: torch.Tensor, tgt_mask: torch.Tensor):
    tgt = self.tgt_embeddings(tgt)
    tgt = self.tgt_pos(tgt)
    return self.decoder(tgt, encoder_output, src_mask, tgt_mask)

  def project(self, x):
    # (batch, seq_len, vocab_size)
    return self.projection_layer(x)

def build_transformer(src_vocab_size: int
                      , tgt_vocab_size: int
                      , src_seq_len: int
                      , tgt_seq_len: int
                      , d_model: int=512
                      , N: int=6
                      , num_heads: int=8
                      , dropout: float=0.1
                      , d_ff: int=2048) -> Transformer:
  # Create embeddings
  src_embed = InputEmbedding(d_model, src_vocab_size)
  tgt_embed = InputEmbedding(d_model, tgt_vocab_size)

  # Create positional encoding layers
  src_pos = PositionalEncoding(d_model, src_seq_len, dropout)
  tgt_pos = PositionalEncoding(d_model, tgt_seq_len, dropout)

  # Create encoder blocks
  encoder_blocks = []
  for _ in range(N):
    encoder_self_attention_block = MultiHeadAttention(d_model, num_heads, dropout)
    feed_forward_block = FeedForward(d_model, d_ff, dropout)
    encoder_block = EncoderBlock(d_model, encoder_self_attention_block, feed_forward_block, dropout)
    encoder_blocks.append(encoder_block)

  # Create decoder blocks
  decoder_blocks = []
  for _ in range(N):
    decoder_mask_attention_block = MultiHeadAttention(d_model, num_heads, dropout)
    decoder_encoder_decoder_attention_block = MultiHeadAttention(d_model, num_heads, dropout)
    feed_forward_block = FeedForward(d_model, d_ff, dropout)
    decoder_block = DecoderBlock(d_model, decoder_mask_attention_block, decoder_encoder_decoder_attention_block, feed_forward_block, dropout)
    decoder_blocks.append(decoder_block)

  # Create the encoder and decoder
  encoder = Encoder(d_model, nn.ModuleList(encoder_blocks))
  decoder = Decoder(d_model, nn.ModuleList(decoder_blocks))

  # Create the projection layer
  projection_layer = ProjectionLayer(d_model, tgt_vocab_size)

  # Create the transformer
  transformer = Transformer(encoder, decoder, src_embed, tgt_embed, src_pos, tgt_pos, projection_layer)

  # Initialize the parameters
  for p in transformer.parameters():
    if p.dim() > 1:
      nn.init.xavier_uniform_(p)
  
  return transformer
