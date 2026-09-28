"""Assessment head(s) — spec section 12/13. One linear head per target
dimension sharing a common trunk, so the model reports interpretable
component scores rather than a single opaque overall number."""
import torch.nn as nn


class MultiTaskAssessmentHead(nn.Module):
    def __init__(self, input_dim: int, targets: tuple, hidden_dim: int = 128):
        super().__init__()
        self.trunk = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Dropout(0.2))
        self.heads = nn.ModuleDict({t: nn.Linear(hidden_dim, 1) for t in targets})
        self.targets = targets

    def forward(self, x):
        h = self.trunk(x)
        return {t: self.heads[t](h).squeeze(-1) for t in self.targets}
