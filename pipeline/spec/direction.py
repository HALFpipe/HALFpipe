# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""

from enum import Enum

phase_encoding_direction_values = [
    "i-",
    "i",
    "j-",
    "j",
    "k-",
    "k",
    "rl",
    "lr",
    "pa",
    "ap",
    "si",
    "is",
]


PhaseEncodingDirection = Enum(
    value="PhaseEncodingDirection",
    names=[
        # axis-based codes
        ("i-", "i-"),
        ("i", "i"),
        ("j-", "j-"),
        ("j", "j"),
        ("k-", "k-"),
        ("k", "k"),
        # space-based codes
        ("rl", "rl"),
        ("RL", "rl"),
        ("right_to_left", "rl"),
        ("rightToLeft", "rl"),
        ("RightToLeft", "rl"),
        ("Right to left", "rl"),
        ("lr", "lr"),
        ("LR", "lr"),
        ("left_to_right", "lr"),
        ("leftToRight", "lr"),
        ("LeftToRight", "lr"),
        ("left to right", "lr"),
        ("Left to right", "lr"),
        ("pa", "pa"),
        ("PA", "pa"),
        ("posterior_to_anterior", "pa"),
        ("posteriorToAnterior", "pa"),
        ("PosteriorToAnterior", "pa"),
        ("Posterior to anterior", "pa"),
        ("ap", "ap"),
        ("AP", "ap"),
        ("anterior_to_posterior", "ap"),
        ("anteriorToPosterior", "ap"),
        ("AnteriorToPosterior", "ap"),
        ("Anterior to posterior", "ap"),
        ("si", "si"),
        ("SI", "si"),
        ("superior_to_inferior", "si"),
        ("superiorToInferior", "si"),
        ("SuperiorToInferior", "si"),
        ("Superior to inferior", "si"),
        ("is", "is"),
        ("IS", "is"),
        ("inferior_to_superior", "is"),
        ("inferiorToSuperior", "is"),
        ("InferiorToSuperior", "is"),
        ("Inferior to superior", "is"),
    ],
)
