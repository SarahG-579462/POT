# -*- coding: utf-8 -*-
"""
Domain adaptation with optimal transport
"""


import autograd.numpy as np
from pymanopt.manifolds import Stiefel
from pymanopt import Problem
from pymanopt.solvers import SteepestDescent, TrustRegions

def dist(x1,x2):
    """ Compute squared euclidena distance between samples
    """
    x1p2=np.sum(np.square(x1),1)    
    x2p2=np.sum(np.square(x2),1)
    return x1p2.reshape((-1,1))+x2p2.reshape((1,-1))-2*np.dot(x1,x2.T)    

def sinkhorn(w1,w2,M,reg,k):
    """
    Simple solver for Sinkhorn algorithm with fixed number of iteration
    """
    K=np.exp(-M/reg)
    ui=np.ones((M.shape[0],))
    vi=np.ones((M.shape[1],))
    for i in range(k):
        vi=w2/(np.dot(K.T,ui))
        ui=w1/(np.dot(K,vi))
    G=ui.reshape((M.shape[0],1))*K*vi.reshape((1,M.shape[1]))   
    return G

def split_classes(X,y):
    """
    split samples in X by classes in y
    """
    lstsclass=np.unique(y)
    return [X[y==i,:].astype(np.float32) for i in lstsclass]
    


def wda(X,y,p=2,reg=1,k=10,solver = None,maxiter=100,verbose=0):
    """ 
    Wasserstein Discriminant Analysis    
    
    The function solves the following optimization problem:

    .. math::
        P = arg\min_P \frac{\sum_i W(PX^i,PX^i)}{\sum_{i,j\neq i} W(PX^i,PX^j)}

    where :

    - :math:`W` is entropic regularized Wasserstein distances
    - :math:`X^i` are samples in the dataset corresponding to class i    
    
    """
    
    mx=np.mean(X)
    X-=mx.reshape((1,-1))
    
    # data split between classes
    d=X.shape[1]
    xc=split_classes(X,y)
    # compute uniform weighs
    wc=[np.ones((x.shape[0]),dtype=np.float32)/x.shape[0] for x in xc]
        
    def cost(P):
        # wda loss
        loss_b=0
        loss_w=0
    
        for i,xi in enumerate(xc):
            xi=np.dot(xi,P)
            for j,xj in  enumerate(xc[i:]):
                xj=np.dot(xj,P)
                M=dist(xi,xj)
                G=sinkhorn(wc[i],wc[j+i],M,reg,k)
                if j==0:
                    loss_w+=np.sum(G*M)
                else:
                    loss_b+=np.sum(G*M)
                    
        # loss inversed because minimization            
        return loss_w/loss_b
    
    
    # declare manifold and problem
    manifold = Stiefel(d, p)    
    problem = Problem(manifold=manifold, cost=cost)
    
    # declare solver and solve
    if solver is None:
        solver= SteepestDescent(maxiter=maxiter,logverbosity=verbose)   
    elif solver in ['tr','TrustRegions']:
        solver= TrustRegions(maxiter=maxiter,logverbosity=verbose)
        
    Popt = solver.solve(problem)
    
    def proj(X):
        return (X-mx.reshape((1,-1))).dot(Popt)
    
    return Popt, proj