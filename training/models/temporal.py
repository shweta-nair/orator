"""Temporal encoders (spec section 10). Each takes a [B, T, D_in] sequence
of per-frame/window embeddings and returns a pooled [B, D_out] representation.
`none` is the frame-level-aggregation baseline (mean pooling) that the
temporal models are compared against in evaluate.py.
"""
import torch
import torch.nn as nn


class MeanPoolBaseline(nn.Module):
    """Experiment 4: no temporal modeling, just average the sequence."""
    def __init__(self, input_dim, output_dim):
        super().__init__()
        self.proj = nn.Linear(input_dim, output_dim)

    def forward(self, x, mask=None):
        # x: [B, T, D_in]
        if mask is not None:
            x = x * mask.unsqueeze(-1)
            pooled = x.sum(1) / mask.sum(1, keepdim=True).clamp(min=1)
        else:
            pooled = x.mean(dim=1)
        return self.proj(pooled)


class LSTMEncoder(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers=2, bidirectional=True):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers,
                             batch_first=True, bidirectional=bidirectional)
        out_dim = hidden_dim * (2 if bidirectional else 1)
        self.out_dim = out_dim

    def forward(self, x, mask=None):
        out, (h, c) = self.lstm(x)
        # concat final layer's forward/backward hidden state as the pooled repr
        if self.lstm.bidirectional:
            last = torch.cat([h[-2], h[-1]], dim=-1)
        else:
            last = h[-1]
        return last


class GRUEncoder(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers=2, bidirectional=True):
        super().__init__()
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers=num_layers,
                           batch_first=True, bidirectional=bidirectional)
        self.out_dim = hidden_dim * (2 if bidirectional else 1)

    def forward(self, x, mask=None):
        out, h = self.gru(x)
        if self.gru.bidirectional:
            last = torch.cat([h[-2], h[-1]], dim=-1)
        else:
            last = h[-1]
        return last


class TransformerEncoder(nn.Module):
    """Optional model (spec section 10, Experiment 7)."""
    def __init__(self, input_dim, hidden_dim, num_layers=2, num_heads=4, max_len=512):
        super().__init__()
        self.in_proj = nn.Linear(input_dim, hidden_dim)
        self.pos_embed = nn.Parameter(torch.randn(1, max_len, hidden_dim) * 0.02)
        layer = nn.TransformerEncoderLayer(d_model=hidden_dim, nhead=num_heads,
                                            batch_first=True, dropout=0.1)
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.out_dim = hidden_dim

    def forward(self, x, mask=None):
        b, t, _ = x.shape
        h = self.in_proj(x) + self.pos_embed[:, :t, :]
        key_padding_mask = ~mask.bool() if mask is not None else None
        h = self.encoder(h, src_key_padding_mask=key_padding_mask)
        if mask is not None:
            h = h * mask.unsqueeze(-1)
            pooled = h.sum(1) / mask.sum(1, keepdim=True).clamp(min=1)
        else:
            pooled = h.mean(dim=1)
        return pooled


def build_temporal_encoder(kind: str, input_dim: int, hidden_dim: int, num_layers: int = 2):
    if kind == "none":
        return MeanPoolBaseline(input_dim, hidden_dim)
    if kind == "lstm":
        return LSTMEncoder(input_dim, hidden_dim, num_layers)
    if kind == "gru":
        return GRUEncoder(input_dim, hidden_dim, num_layers)
    if kind == "transformer":
        return TransformerEncoder(input_dim, hidden_dim, num_layers)
    raise ValueError(f"unknown temporal encoder kind: {kind}")
