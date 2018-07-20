from __future__ import print_function
import numpy as np
import utils
from numpy import linalg as LA
import math

def ODL_updateD(D, E, F, iterations = 100, tol = 1e-8):
    """
    * The main algorithm in ODL.
    * Solving the optimization problem:
      `D = arg min_D -2trace(E'*D) + trace(D*F*D')` subject to: `||d_i||_2 <= 1`,
         where `F` is a positive semidefinite matrix.
    * Syntax `[D, iter] = ODL_updateD(D, E, F, opts)`
      - INPUT:
        + `D, E, F` as in the above problem.
        + `opts`. options:
          * `iterations`: maximum number of iterations.
          * `tol`: when the difference between `D` in two successive
                    iterations less than this value, the algorithm will stop.
      - OUTPUT:
        + `D`: solution.
    -----------------------------------------------
    Author: Tiep Vu, thv102@psu.edu, 04/07/2016
            (http://www.personal.psu.edu/thv102/)
    -----------------------------------------------
    """
    def calc_cost(D):
        return -2*np.trace(np.dot(E, D.T)) + np.trace(np.dot(np.dot(F, D.T), D))

    D_old = D.copy()
    it = 0
    sizeD = utils.numel(D)
    # print opts.tol
    # while it < opts.max_iter:
    for it in range(iterations):
        for i in xrange(D.shape[1]):
            if F[i,i] != 0:
                a = 1.0/F[i,i] * (E[:, i] - D.dot(F[:, i])) + D[:, i]
                D[:,i] = a/max(LA.norm(a, 2), 1)

        if LA.norm(D - D_old, 'fro')/sizeD < tol:
            break
        D_old = D.copy()
    return D


def DLSI_updateD(D, E, F, A, lambda1, verbose = False, iterations = 100):
    """
    def DLSI_updateD(D, E, F, A, lambda1, verbose = False, iterations = 100):
    problem: `D = argmin_D -2trace(ED') + trace(FD'*D) + lambda *||A*D||F^2,`
    subject to: `||d_i||_2^2 <= 1`
    where F is a positive semidefinite matrix
    ========= aproach: ADMM ==============================
    rewrite: `[D, Z] = argmin -2trace(ED') + trace(FD'*D) + lambda ||A*Z||_F^2,`
        subject to `D = Z; ||d_i||_2^2 <= 1`
    aproach 1: ADMM.
    1. D = -2trace(ED') + trace(FD'*D) + rho/2 ||D - Z + U||_F^2,
        s.t. ||d_i||_2^2 <= 1
    2. Z = argmin lambda*||A*Z|| + rho/2||D - Z + U||_F^2
    3. U = U + D - Z
    solve 1: D = argmin -2trace(ED') + trace(FD'*D) + rho/2 ||D - W||_F^2
                          with W = Z - U;
               = argmin -2trace((E - rho/2*W)*D') +
                  trace((F + rho/2 * eye())*D'D)
    solve 2: derivetaive: 0 = 2A'AZ + rho (Z - V) with V = D + U
    `Z = B*rhoV` with `B = (2*lambda*A'*A + rho I)^{-1}`
    `U = U + D - Z`
    -----------------------------------------------
    Author: Tiep Vu, thv102@psu.edu, 5/11/2016
            (http://www.personal.psu.edu/thv102/)
    -----------------------------------------------
    """
    def calc_cost(D):
        cost = -2*np.trace(np.dot(E, D.T)) + np.trace(np.dot(F, np.dot(D.T, D))) +\
            lambda1*utils.normF2(np.dot(A, D))
        return cost
    it    = 0
    rho   = 1.0
    Z_old = D.copy()
    U     = np.zeros_like(D)
    I_k   = np.eye(D.shape[1])
    X     = 2*lambda1/rho*A.T
    Y     = A.copy()
    B1    = np.dot(X, utils.inv_IpXY(Y, X))

    # B1 = np.dot(X, LA.inv(eye(Y.shape[0]) + np.dot(Y, X)))
    tol = 1e-8
    for it in range(iterations):
        it += 1
        # update D
        W  = Z_old - U
        E2 = E + rho/2*W
        F2 = F + rho/2*I_k
        D  = ODL_updateD(D, E2, F2)
        # update Z
        V     = D + U
        Z_new = rho*(V - np.dot(B1, np.dot(Y, V)))
        e1    = utils.normF2(D - Z_new)
        e2    = rho*utils.normF2(Z_new - Z_old)
        if e1 < tol and e2 < tol:
            break
        U     = U + D - Z_new
        Z_old = Z_new.copy()

    return D


class Fista(object):
    def __init__(self):
        pass

    def solve(self, Y, Xinit = None, iterations = 100, tol = 1e-8, verbose = False):
        self.fit(Y)
        if Xinit is None:
            Xinit = np.zeros((self.D.shape[1], self.Y.shape[1]))
        Linv = 1/self.L
        lambdaLiv = self.lamb/self.L
        x_old = Xinit.copy()
        y_old = Xinit.copy()
        t_old = 1
        it = 0
        # cost_old = float("inf")
        for it in range(iterations):
            x_new = np.real(utils.shrinkage(y_old - Linv*self._grad(y_old), lambdaLiv))
            t_new = .5*(1 + math.sqrt(1 + 4*t_old**2))
            y_new = x_new + (t_old - 1)/t_new * (x_new - x_old)
            e = utils.norm1(x_new - x_old)/x_new.size
            if e < tol:
                break
            x_old = x_new.copy()
            t_old = t_new
            y_old = y_new.copy()
            if verbose:
                print('iter \t%d/%d, loss \t %4.4f'%(it + 1, iterations, self.lossF(x_new)))
        return x_new


class Lasso(Fista):
    """
    Solving a Lasso problem using FISTA
    `X, = arg min_X 0.5*||Y - DX||_F^2 + lambd||X||_1
        = argmin_X f(X) + lambd||X||_1
        F(x) = f(X) + lamb||X||_1
    """
    def __init__(self, D, lamb = .1):
        self.D = D
        self.lamb = lamb
        self.DtD = np.dot(self.D.T, self.D)
        self.Y = None
        self.DtY = None
        self.L = np.max(LA.eig(self.DtD)[0])

    def fit(self, Y):
        self.Y = Y
        self.DtY = np.dot(self.D.T, self.Y)

    def _grad(self, X):
        return np.dot(self.DtD, X) - self.DtY

    def _calc_f(self, X):
        return 0.5*utils.normF2(self.Y - np.dot(self.D, X))

    def lossF(self, X):
        return self._calc_f(X) + self.lamb*utils.norm1(X)


def _test_lasso():
    d = 3
    N = 7
    k = 7
    Y = utils.normc(np.random.rand(d, N))
    D = utils.normc(np.random.rand(d, k))
    l = Lasso(D, lamb = .01)
    l.fit(Y)
    X = l.solve(verbose = True)
    print(X)


if __name__ == '__main__':
    _test_lasso()