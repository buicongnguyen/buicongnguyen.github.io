"""Deliberately broken: diagnose the update rule before editing it."""
import numpy as np


def train(seed=7, steps=300, learning_rate=0.2):
    rng=np.random.default_rng(seed); x=rng.normal(size=(200,2)); y=(x[:,0]+0.5*x[:,1]>0).astype(float)
    weights=np.zeros(2); bias=0.0; losses=[]
    for _ in range(steps):
        logits=x@weights+bias; probability=1/(1+np.exp(-np.clip(logits,-30,30)))
        losses.append(float(-np.mean(y*np.log(probability+1e-9)+(1-y)*np.log(1-probability+1e-9))))
        error=probability-y; grad_w=x.T@error/len(x); grad_b=error.mean()
        weights += learning_rate*grad_w  # planted defect: gradient ascent
        bias += learning_rate*grad_b
    return np.asarray(losses), ((x@weights+bias>=0)==y).mean()
