"""Explicit rating prediction, kept deliberately separate from NeuMF ranking.

The NeuMF ranking head produces an uncalibrated logit, which must never be
presented as a star rating. This model shares the NeuMF *trunk* shape but is
trained with MSE on the real 0.5-5.0 ratings and squashes its output through

    rating = RATING_MIN + (RATING_MAX - RATING_MIN) * sigmoid(x)

so every prediction is structurally inside the MovieLens rating scale.
Evaluated with RMSE / MAE.
"""

from __future__ import annotations

import torch
from torch import nn

from ml.models.neumf import NeuMF


class RatingPredictor(nn.Module):
    def __init__(
        self,
        n_users: int,
        n_movies: int,
        gmf_dim: int = 32,
        mlp_dim: int = 32,
        mlp_layers: list[int] | None = None,
        dropout: float = 0.1,
        rating_min: float = 0.5,
        rating_max: float = 5.0,
    ):
        super().__init__()
        self.trunk = NeuMF(n_users, n_movies, gmf_dim, mlp_dim, mlp_layers, dropout)
        self.rating_min = rating_min
        self.rating_max = rating_max
        self.user_bias = nn.Embedding(n_users, 1)
        self.item_bias = nn.Embedding(n_movies, 1)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.item_bias.weight)

    @property
    def n_users(self) -> int:
        return self.trunk.n_users

    @property
    def n_movies(self) -> int:
        return self.trunk.n_movies

    def raw(self, users: torch.Tensor, items: torch.Tensor) -> torch.Tensor:
        return (self.trunk(users, items)
                + self.user_bias(users).squeeze(-1)
                + self.item_bias(items).squeeze(-1))

    def forward(self, users: torch.Tensor, items: torch.Tensor) -> torch.Tensor:
        """Predicted rating, calibrated into [rating_min, rating_max]."""
        span = self.rating_max - self.rating_min
        return self.rating_min + span * torch.sigmoid(self.raw(users, items))

    def forward_from_user_vectors(
        self, gmf_u: torch.Tensor, mlp_u: torch.Tensor,
        user_bias: torch.Tensor, items: torch.Tensor,
    ) -> torch.Tensor:
        """Calibrated rating for a cold-start user held as explicit vectors."""
        raw = (self.trunk.forward_from_user_vectors(gmf_u, mlp_u, items)
               + user_bias
               + self.item_bias(items).squeeze(-1))
        span = self.rating_max - self.rating_min
        return self.rating_min + span * torch.sigmoid(raw)

    def config(self) -> dict:
        cfg = self.trunk.config()
        cfg.update({
            "architecture": "NeuMF trunk + calibrated regression head",
            "objective": "MSE on explicit ratings",
            "output": "predicted rating",
            "rating_scale": [self.rating_min, self.rating_max],
            "calibration": "rating_min + (rating_max - rating_min) * sigmoid(x)",
        })
        return cfg
