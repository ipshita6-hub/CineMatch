"""NeuMF - Neural Collaborative Filtering (He et al., WWW 2017).

Two independent branches that do NOT share embeddings:

  GMF : user/item embeddings -> element-wise product        (linear interaction)
  MLP : separate user/item embeddings -> concat -> FC stack (non-linear)

Their outputs are concatenated into the NeuMF layer, which produces a single
logit. Trained with BCE-with-logits on observed positives vs. sampled
unobserved items.
"""

from __future__ import annotations

import torch
from torch import nn


class NeuMF(nn.Module):
    def __init__(
        self,
        n_users: int,
        n_movies: int,
        gmf_dim: int = 32,
        mlp_dim: int = 32,
        mlp_layers: list[int] | None = None,
        dropout: float = 0.1,
    ):
        super().__init__()
        mlp_layers = list(mlp_layers or [64, 32, 16])

        self.n_users = n_users
        self.n_movies = n_movies
        self.gmf_dim = gmf_dim
        self.mlp_dim = mlp_dim
        self.mlp_layers = mlp_layers
        self.dropout = dropout

        # --- GMF branch -------------------------------------------------
        self.gmf_user_emb = nn.Embedding(n_users, gmf_dim)
        self.gmf_item_emb = nn.Embedding(n_movies, gmf_dim)

        # --- MLP branch (separate embedding tables, per the paper) ------
        self.mlp_user_emb = nn.Embedding(n_users, mlp_dim)
        self.mlp_item_emb = nn.Embedding(n_movies, mlp_dim)

        layers: list[nn.Module] = []
        in_dim = mlp_dim * 2
        for out_dim in mlp_layers:
            layers.append(nn.Linear(in_dim, out_dim))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_dim = out_dim
        self.mlp = nn.Sequential(*layers)

        # --- NeuMF fusion ----------------------------------------------
        self.predict = nn.Linear(gmf_dim + mlp_layers[-1], 1)

        self._init_weights()

    def _init_weights(self) -> None:
        for emb in (self.gmf_user_emb, self.gmf_item_emb,
                    self.mlp_user_emb, self.mlp_item_emb):
            nn.init.normal_(emb.weight, std=0.01)
        for m in self.mlp:
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
        nn.init.xavier_uniform_(self.predict.weight)
        nn.init.zeros_(self.predict.bias)

    def interaction_vector(self, users: torch.Tensor, items: torch.Tensor) -> torch.Tensor:
        gmf = self.gmf_user_emb(users) * self.gmf_item_emb(items)
        mlp_in = torch.cat([self.mlp_user_emb(users), self.mlp_item_emb(items)], dim=-1)
        mlp = self.mlp(mlp_in)
        return torch.cat([gmf, mlp], dim=-1)

    def forward(self, users: torch.Tensor, items: torch.Tensor) -> torch.Tensor:
        """Returns a raw logit. This is a ranking score, never a star rating."""
        return self.predict(self.interaction_vector(users, items)).squeeze(-1)

    def forward_from_user_vectors(
        self, gmf_u: torch.Tensor, mlp_u: torch.Tensor, items: torch.Tensor
    ) -> torch.Tensor:
        """Score items for a user represented by explicit vectors.

        Used by the cold-start fold-in path, where a brand new application
        account has embedding vectors fitted at request time while every item
        parameter stays frozen.
        """
        gmf = gmf_u.unsqueeze(0) * self.gmf_item_emb(items)
        mlp_in = torch.cat([mlp_u.unsqueeze(0).expand(items.shape[0], -1),
                            self.mlp_item_emb(items)], dim=-1)
        return self.predict(torch.cat([gmf, self.mlp(mlp_in)], dim=-1)).squeeze(-1)

    def config(self) -> dict:
        return {
            "architecture": "NeuMF (GMF + MLP fusion), He et al. WWW 2017",
            "num_users": self.n_users,
            "num_movies": self.n_movies,
            "gmf_embedding_dim": self.gmf_dim,
            "mlp_embedding_dim": self.mlp_dim,
            "mlp_layers": self.mlp_layers,
            "dropout": self.dropout,
            "fusion_input_dim": self.gmf_dim + self.mlp_layers[-1],
            "output": "single logit (implicit-feedback ranking score)",
        }
