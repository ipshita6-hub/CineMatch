"""Implicit Matrix Factorization baseline.

Architecture carried over unchanged from section 22 of the original Colab
notebook so that the baseline it reports stays directly comparable. Score is a
dot product plus user/item/global biases, trained with BCE-with-logits against
sampled unobserved items.
"""

from __future__ import annotations

import torch
from torch import nn


class MatrixFactorization(nn.Module):
    def __init__(self, n_users: int, n_movies: int, dim: int = 32):
        super().__init__()
        self.n_users = n_users
        self.n_movies = n_movies
        self.dim = dim

        self.user_emb = nn.Embedding(n_users, dim)
        self.movie_emb = nn.Embedding(n_movies, dim)
        self.user_bias = nn.Embedding(n_users, 1)
        self.movie_bias = nn.Embedding(n_movies, 1)
        self.global_bias = nn.Parameter(torch.zeros(1))

        nn.init.normal_(self.user_emb.weight, std=0.05)
        nn.init.normal_(self.movie_emb.weight, std=0.05)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.movie_bias.weight)

    def forward(self, users: torch.Tensor, movies: torch.Tensor) -> torch.Tensor:
        dot = (self.user_emb(users) * self.movie_emb(movies)).sum(dim=1)
        bias = self.user_bias(users).squeeze(1) + self.movie_bias(movies).squeeze(1)
        return dot + bias + self.global_bias

    def config(self) -> dict:
        return {
            "architecture": "Matrix Factorization (implicit, BPR-style BCE)",
            "num_users": self.n_users,
            "num_movies": self.n_movies,
            "embedding_dim": self.dim,
            "interaction": "dot product + user/item/global bias",
        }
