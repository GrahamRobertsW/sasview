"""
Converted invertor.c's methods

Currently testing multiple methods of implementing these methods with njit() vector operations etc.
"""
import numpy as np
#from numpy import pi
import sys
import math
import time
import copy
import os
import re
import logging
import time

import timeit
from functools import reduce
pi = 3.1416 #to pass tests
from numba import jit, njit, vectorize, float64, guvectorize, prange, generated_jit
try:
    USE_NUMBA = True
except ImportError:
    USE_NUMBA = False

def conditional_decorator(dec, condition):
    """
    If condition is true returns dec(func).
    Returns the function with decorator applied otherwise
    uses default.
    Called by @conditional_decorator(dec, condition)
              def():
    """
    def decorator(func):
        if not condition:
            return func
        return dec(func)
    return decorator

@conditional_decorator(njit('f8(f8, f8)'), USE_NUMBA)
def pr_sphere(R, r):
    """
    P(r) of a sphere, for test purposes

    @param R: radius of the sphere
    @param r: distance, in same units as the radius
    @return: P(r)
    """
    if(r <= 2.0*R):
        return 12.0* (0.5*r/R)**2 * (1.0-0.5*r/R)**2 * (2.0+0.5*r/R)
    else:
        return 0

@conditional_decorator(njit('f8(f8, u8, f8)'), USE_NUMBA)
def ortho(d_max, n, r):
    """
    Orthogonal Functions:
    B(r) = 2r sin(pi*nr/d)
    """
    return 2.0 * r * np.sin(pi*n*r/d_max)

@conditional_decorator(njit('f8(f8, u8, f8)'), USE_NUMBA)
def ortho_transformed(d_max, n, q):
    """
    Fourier transform of the nth orthagonal function

    With vectorize time was
    \@vectorize() ~= 1.4e-05
    \@njit() ~= 3e-06
    \@njit(parallel=True) - Compiler returns no transformation for parallel execution possible
    and time was the same as @njit()
    """
    return 8.0*(pi)**2/q * d_max * n * (-1.0)**(n+1) * math.sin(q*d_max) / ( (pi*n)**2 - (q*d_max)**2 )
    #qd = q * (d_max/pi)
    #return ( 8.0 * d_max**2/pi * n * (-1.0)**(n+1) ) * np.sinc(qd) / (n**2 - qd**2)

@conditional_decorator(njit('f8(f8, u8, f8, f8, f8, u8)'), USE_NUMBA)
def ortho_transformed_smeared(d_max, n, height, width, q, npts):
    """
    Slit-smeared Fourier transform of the nth orthagonal function.
    Smearing follows Lake, Acta Cryst. (1967) 23, 191.

    \@njit() - 5 - time roughly 4.5e-05
    \@njit() - npts 1000 - 0.031
    \@njit(parallel = True) - no transformation possible same time.
    \@vectorize([float64(float64, float64, float64, float64, float64, float64)])  npts = 5 ~= 1.6e-05
    npts = 1000 ~= 0.02
    """
    y = 0
    z = 0
    sum = 0

    i = 0
    j = 0
    n_height = 0
    n_width = 0
    count_w = 0
    fnpts = 0
    sum = 0.0
    fnpts = float(npts-1.0)
    if(height > 0):
        n_height = npts
    else:
        n_height = 1
    if(width > 0):
        n_width = npts
    else:
        n_width = 1

    count_w = 0.0

    #Pre compute dz, y0 and dy
    dz = height/(npts-1)
    y0 = -0.5*width
    dy = width/(npts-1)

    for j in range(0, n_height):
        zsq = (j * dz)**2

        for i in range(0, n_width):
            y = y0 + i*dy
            qsq = (q - y)**2 + zsq
            count_w += qsq > 0
            sum += ortho_transformed(d_max, n, np.sqrt(qsq))
    return sum / count_w

@conditional_decorator(njit('f8(f8, u8, f8)'), USE_NUMBA)
def ortho_derived(d_max, n, r):
    """
    First derivative in of the orthogonal function dB(r)/dr
    """
    pinr = pi * n * r/d_max
    return 2.0 * np.sin(pinr) + 2.0 * r * np.cos(pinr)

@conditional_decorator(njit('f8(f8[:], f8, f8)'), USE_NUMBA)
def iq(pars, d_max, q):
    """
    Scattering intensity calculated from the expansion

    Dataset of 10,000 pars 302 q
    using njit, parallel ~= 0.04
    using njit default ~= 0.11
    using vectorize ~= 7
    using default python ~= 18
    """
    #q = np.asanyarray(q)
    sum = 0.0
    for i in range(len(pars)):
        #for j in prange(q.shape[0]):
        sum += pars[i] * ortho_transformed(d_max, i + 1, q)
    return sum

@conditional_decorator(njit('f8(f8[:], f8, f8, f8, f8, u8)'), USE_NUMBA)
def iq_smeared(pars, d_max, height, width, q, npts):
    """
    Scattering intensity calculated from expansion,
    slit smeared.

    for test data of size 20 ~= 0.0005 basic
    ~= 0.0003 njit
    ~= 0.12 using numba vectorize()
    Couldn't use njit and vectorize in same method, looked on
    github seems to be issue for a long time with numba.
    Maybe faster if work together ?
    njit() compilation only slightly faster. Maybe with working
    njit() and vector operations be faster.

    iq_smeared(np.arange(10000), 3, 100, 100, 30, 400) - no parallel - 75
    - parallel - 23.13, over 3x speedup.

    """
    sum = 0.0

    for i in range(len(pars)):
        sum += pars[i] * ortho_transformed_smeared(d_max, i + 1, height, width, q, npts)
    return sum

@conditional_decorator(njit('f8(f8[:], f8, f8)'), USE_NUMBA)
def pr(pars, d_max, r):
    """
    P(r) calculated from the expansion
    """
    sum = 0.0
    for i in range(pars.shape[0]):
        sum += pars[i] * ortho(d_max, i+1, r)
    return sum

@conditional_decorator(njit('f8[:](f8[:], f8[:,:], f8, f8)'), USE_NUMBA)
def pr_err(pars, err, d_max, r):
    """
    P(r) calculated from the expansion,
    with errors
    changed to instead of return value by reference, returns
    tuple of (pr_value, pr_value_err)
    """
    sum = 0.0
    sum_err = 0.0
    func_value = 0
    n_c = pars.shape[0]

    for i in range(n_c):
        func_value = ortho(d_max, i+1, r)
        sum += pars[i] * func_value
        sum_err += err[i, i] * func_value * func_value

    pr_value = sum
    if(sum_err > 0):
        pr_value_err = np.sqrt(sum_err)
    else:
        pr_value_err = sum

    ret = np.zeros(2, dtype = np.float64)
    ret[0] = pr_value
    ret[1] = pr_value_err

    return ret

@conditional_decorator(njit('f8(f8[:], f8, f8)'), USE_NUMBA)
def dprdr(pars, d_max, r):
    #test sample 10,000 - 0.00039/38
        #adv - 0.00048

    sum = 0.0
    #300, 2.5e-05
    for i in range(0, pars.shape[0]):
        sum += pars[i] * 2.0*(np.sin(pi*(i+1)*r/d_max) + pi*(i+1)*r/d_max * np.cos(pi*(i+1)*r/d_max))
    return sum



#mp methods
def iq_smeared_mp(p, q, d_max, height, width, npts):
    total = q*0
    for k, pk in enumerate(p):
         total += pk * ortho_transformed_smeared_mp(q, d_max, k+1, height, width, npts)
    return total

def ortho_transformed_smeared_mp(q, d_max, n, height, width, npts):
    import mpmath as mp
    n_width = npts if width > 0 else 1
    n_height = npts if height > 0 else 1
    dz = height/(npts-1)
    y0, dy = -width/2, width/(npts-1)
    total = q*0
    # note: removing count_w since ortho now handles q=0 case
    for j in range(n_height):
        zsq = (j * dz)**2
        for i in range(n_width):
            y = y0 + i*dy
            qsq = (q - y)**2 + zsq
            total += ortho_transformed_mp(mp.sqrt(qsq), d_max, n)
    return total / (n_width*n_height)

def ortho_transformed_mp(q, d_max, n):
    import mpmath as mp
    qd = q * (d_max/mp.pi)
    return ( 8 * d_max**2/mp.pi * n * (-1.0)**(n+1) ) * mp.sincpi(qd) / (n**2 - qd**2)

def check_mp(bits=500):
    import mpmath as mp
    from mpmath import mpf
    with mp.workprec(bits):
        npts = 30
        one = mp.mpf(1)
        q = mp.linspace(one/1000, one/2, 5)
        p = mp.arange(40)
        d_max = one*2000
        width, height = one/100, one*3
        mp_result = [iq_smeared_mp(p, qk, d_max, height, width, npts) for qk in q]

        p = np.array([float(pk) for pk in p])
        q = np.array([float(qk) for qk in q])
        d_max = float(d_max)
        width, height = float(width), float(height)
        np_result = iq_smeared_qvec(p, q, d_max, height, width, npts)
        njit_result = iq_smeared_qvec_njit(p, q, d_max, height, width, npts)

        for qk, mpk, npk, jitk in zip(q, mp_result, np_result, njit_result):
            #print(qk, mpk, npk, float((mpk-npk)/mpk))
            print(qk, float(mpk), npk, jitk, "err", float((mpk-npk)/mpk), float((mpk-jitk)/mpk))

#qvec methods
def iq_smeared_qvec(p, q, d_max, height, width, npts):
    total = np.zeros_like(q)
    for i, pi in enumerate(p):
         total += pi * ortho_transformed_smeared_qvec(q, d_max, i+1, height, width, npts)
    return total

def ortho_transformed_smeared_qvec(q, d_max, n, height, width, npts):
    n_width = npts if width > 0 else 1
    n_height = npts if height > 0 else 1
    dz = height/(npts-1)
    y0, dy = -0.5*width, width/(npts-1)
    total = np.zeros(len(q), dtype='d')
    # note: removing count_w since ortho now handles q=0 case
    for j in range(n_height):
        zsq = (j * dz)**2
        for i in range(n_width):
            y = y0 + i*dy
            qsq = (q - y)**2 + zsq
            total += ortho_transformed_qvec(np.sqrt(qsq), d_max, n)
    return total / (n_width*n_height)

def ortho_transformed_qvec(q, d_max, n):
    #qd = q * (d_max/pi)
    #return ( 8.0 * d_max**2 * n * (-1.0)**(n+1) ) * np.sinc(qd) / (n**2 - qd**2)
    #Equivalent to C -
    return 8.0*(pi)**2/q * d_max * n * (-1.0)**(n+1) * np.sin(q*d_max) / ( (pi*n)**2 - (q*d_max)**2 )

@conditional_decorator(njit('f8[:](f8[:], f8, u8)'), USE_NUMBA)
def ortho_transformed_qvec_njit(q, d_max, n):
    #qd = q * (d_max/pi)
    #return ( 8.0 * d_max**2 * n * (-1.0)**(n+1) ) * np.sinc(qd) / (n**2 - qd**2)
    #equivalent to C -
    return 8.0*(pi)**2/q * d_max * n * (-1.0)**(n+1) * np.sin(q*d_max) / ( (pi*n)**2 - (q*d_max)**2 )

@conditional_decorator(njit('f8[:](f8[:], f8, u8, f8, f8, u8)'), USE_NUMBA)
def ortho_transformed_smeared_qvec_njit(q, d_max, n, height, width, npts):
    n_width = npts if width > 0 else 1
    n_height = npts if height > 0 else 1
    dz = height/(npts-1)
    y0, dy = -0.5*width, width/(npts-1)
    total = np.zeros(len(q), dtype=np.float64)
    #total = np.zeros_like(q)
    # note: removing count_w since ortho now handles q=0 case

    for j in range(n_height):
        zsq = (j * dz)**2
        #temp = np.zeros(np.uint8(n_width), dtype = np.float64)
        for i in range(n_width):
            y = y0 + i*dy
            qsq = (q - y)**2 + zsq
            total += ortho_transformed_qvec_njit(np.sqrt(qsq), d_max, n)
    return total / (n_width*n_height)

#qvec methods with numba
@conditional_decorator(njit('f8[:](f8[:], f8[:], f8, f8, f8, u8)'), USE_NUMBA)
def iq_smeared_qvec_njit(p, q, d_max, height, width, npts):
    size_q = len(q)
    size_p = len(p)

    total = np.zeros(size_q, dtype=np.float64)
    for i in range(size_p):
        total += p[i] * ortho_transformed_smeared_qvec_njit(q, d_max, i+1, height, width, npts)
    return total






@conditional_decorator(njit('f8(f8[:], f8, u8)'), USE_NUMBA)
def reg_term(pars, d_max, nslice):
    """
    Regularization term calculated from the expansion.
    """
    sum = 0.0
    r = 0.0
    deriv = 0.0
    #pre computing, implicitly convering nslice to double
    #as originally done in loop
    for i in range(nslice):
        r = d_max/(1.0 * nslice)*i
        deriv = dprdr(pars, d_max, r)
        sum += deriv*deriv

    return sum/(1.0 * nslice)* d_max

@conditional_decorator(njit('f8(f8[:], f8, u8)'), USE_NUMBA)
def int_p2(pars, d_max, nslice):
    """
    Regularization term calculated from the expansion.
    """
    sum = 0.0
    r = 0.0
    value = 0.0
    nslice_d = 1.0 * nslice
    for i in range(nslice):
        r = d_max/nslice_d * i
        value = pr(pars, d_max, r)
        sum += value * value
    return sum/nslice_d * d_max

@conditional_decorator(njit('f8(f8[:], f8, u8)'), USE_NUMBA)
def int_pr(pars, d_max, nslice):
    """
    Integral of P(r)
    """
    sum = 0.0
    r = 0.0
    value = 0.0
    nslice_d = 1.0 * nslice
    for i in range(nslice):
        r = d_max/nslice_d * i
        value = pr(pars, d_max, r)
        sum += value
    return sum/nslice_d * d_max

@conditional_decorator(njit('u8(f8[:], f8, u8)'), USE_NUMBA)
def npeaks(pars, d_max, nslice):
    """
    Get the number of P(r) peaks
    """
    r = 0.0
    value = 0.0
    previous = 0.0
    slope = 0.0
    count = 0
    nslice_d = nslice * 1.0
    for i in range(nslice):
        r = d_max/nslice_d * i
        value = pr(pars, d_max, r)
        #print("i: ", value)
        if(previous<=value):
            slope = 1
        else:
            if(slope>0):
                count = count + 1
            slope = -1
        previous = value

    return count

@conditional_decorator(njit('f8(f8[:], f8, u8)'), USE_NUMBA)
def positive_integral(pars, d_max, nslice):
    """
    Get the fraction of the integral of P(r) over the whole
    range of r that is above 0.
    A valid P(r) is defined as being positive for all r.

    Parallelization of this method gives ~=40% speedup.
    """
    r = 0.0
    value = 0.0
    sum_pos = 0.0
    sum = 0.0
    nslice_d = 1.0 * nslice
    for i in range(nslice):
        r = d_max/nslice_d * i
        value = pr(pars, d_max, r)
        if(value>0.0):
           sum_pos += value
        sum += math.fabs(value)
    return sum_pos / sum

@conditional_decorator(njit('f8(f8[:], f8[:,:], f8, u8)'), USE_NUMBA)
def positive_errors(pars, err, d_max, nslice):
    """
    Get the fraction of the integral of P(r) over the whole range
    of r that is at least one sigma above 0.
    """
    r = 0.0
    sum_pos = 0.0
    sum = 0.0
    nslice_d = 1.0 * nslice
    for i in range(nslice):
        r = d_max/nslice_d * i
        (pr_val, pr_val_err) = pr_err(pars, err, d_max, r)
        if(pr_val>pr_val_err):
            sum_pos += pr_val
        sum += np.fabs(pr_val)
    return sum_pos/sum

@conditional_decorator(njit('f8(f8[:], f8, u8)'), USE_NUMBA)
def rg(pars, d_max, nslice):
    """
    R_g radius of gyration calculation

    R_g**2 = integral[r**2 * p(r) dr] / (2.0 * integral[p(r) dr])
    """
    sum_r2 = 0.0
    sum = 0.0
    r = 0.0
    value = 0.0
    for i in range(nslice):
        r = (d_max/nslice) * i
        value = pr(pars, d_max, r)
        sum += value
        sum_r2 += r*r*value

    return np.sqrt(sum_r2/(2.0*sum))




#testing
#@njit()
def speed_test_njit(x):

    result = np.zeros([x.shape[0]])

    for i, xi in enumerate(x):
        result[i] = xi * xi
    return result

def speed_test_vec(x):

    @vectorize([float64(float64)])
    def multiply(y):
        return y * y
    multiply(x)
def speed_test_numpy_vec(x):

    def multiply(y):
        return y * y
    f = np.vectorize(multiply)
    f(x)

@generated_jit(nopython = True)
def gen_jit_test(x):
    temp = 1
    for i in range(40):
        temp *= x[i]
    return temp

@njit(cache = True)
def jit_test(x):
    temp = 1
    for i in range(40):
        temp *= x[i]
    return temp

def demo_genjit():
    setup = '''
from __main__ import jit_test, gen_jit_test
import numpy as np
x = np.arange(40)'''
    run_gen = '''
gen_jit_test(x)
    '''
    run = '''
jit_test(x)
    '''
    print("Gen_jit: ", timeit.repeat(setup = setup, stmt = run_gen, repeat = 10, number = 1))
    print("Gen: ", timeit.repeat(setup = setup, stmt = run, repeat = 10, number = 1))

#@njit(cache = True)
@njit(cache = True)
def cache_test(x):
    return x ** 2

@njit()
def test(x):
    return x ** 2

def cache_demo():
    setup = '''
from __main__ import cache_test
from __main__ import test
import numpy as np
x = np.arange(1000)
'''
    run_cache = '''
cache_test(x)
'''
    run = '''
test(x)
'''
    cache_time = timeit.repeat(stmt = run_cache, setup = setup, repeat = 10, number = 1)
    n_time = timeit.repeat(stmt = run, setup = setup, repeat = 10, number = 1)

    print("Cache: ", cache_time)
    print("N Time: ", n_time)

def demo_speedtest():
    setup = '''
from __main__ import speed_test_njit
from __main__ import speed_test_vec
from __main__ import speed_test_numpy_vec
import numpy as np
x = np.arange(1000000)
'''
    run_njit = '''
speed_test_njit(x)
'''
    run_vec = '''
speed_test_vec(x)
'''
    run_np = '''
speed_test_numpy_vec(x)
'''
    print(timeit.repeat(setup = setup, stmt = run_njit, repeat = 10, number = 1))
    print(timeit.repeat(setup = setup, stmt = run_vec, repeat = 10, number = 1))
    print(timeit.repeat(setup = setup, stmt = run_np, repeat = 10, number = 1))

def demo_npeaks():
    setup = '''
from __main__ import npeaks
from __main__ import npeaks_alt
import numpy as np
pars = np.arange(40)
d_max = 2000
nslice = 1000'''
    run = '''
npeaks(pars, d_max, nslice)
    '''
    run2 = '''
npeaks_alt(pars, d_max, nslice)
'''
    print(timeit.repeat(setup = setup, stmt = run, repeat = 10, number = 1))
    print(timeit.repeat(setup = setup, stmt = run2, repeat = 10, number = 1))

def demo_rearrange():
    func1 = lambda q, d_max, n : 8 * (pi)**2/ q * d_max * n * (-1)**(n + 1)
    func2 = lambda q, d_max, n : (8 * (pi)**2 * d_max * n * (-1)**(n + 1))/q

    print(func1(0.5, 2000, 30))
    print(func2(0.5, 2000, 30))

def demo_dp():
    pars = np.arange(2000)
    time1 = time.clock()
    dprdr(pars, 104, 8)
    end1 = time.clock()
    time2 = time.clock()
    dprdr_vec(pars, 104, 8)
    end2 = time.clock()
    print("time 1: ", end1 - time1)
    print("time 2: ", end2 - time2)


def demo_ot():
    print(pr(np.arange(100), 20, 100))
def demo_ortho():
    q = 0.05

    print(ortho_transformed_qvec_njit(q, 2000, 30))

def demo_c_equiv():
    #q = 0.05
    p = np.arange(40)
    #print(p)
    d_max = 2000
    width, height = 0.01, 3
    npts = 30
    q = np.linspace(0.001, 0.5, 301)
    setup = '''
from __main__ import iq_smeared_qvec_njit
import numpy as np
p = np.arange(40)
print(p)
d_max = 2000
width, height = 0.01, 3
npts = 30
q = np.linspace(0.001, 0.5, 301)
print("Working q: ", q.shape)
print(q)'''
    run = '''
iq_smeared_qvec(p, q, d_max, height, width, npts)'''
    #times = timeit.repeat(setup = setup, stmt = run, repeat = 10, number = 1)
    #print(times)
    for i in range(q.shape[0]):
        q[i] = 0.01 + (0.00166 * i)
    print(q)
    print("Result:", np.sum(iq_smeared_qvec(p, q, d_max, height, width, npts)))







def demo():
    tests = 6
    testVals = np.zeros([tests,2])

    for j in range(0, tests):
        coeff = np.arange(100)
        minq = 0
        maxq = 30000
        d_max = 30

        start = time.clock()
        x = np.linspace(minq, maxq, 301)
        print(x.shape)
        y = np.zeros_like(x)
        for i, qi in enumerate(x):
            y[i] = iq(coeff, d_max, qi)
        end = time.clock()

        testVals[j][0] = (end - start)
        print("Time elapsed 1 : %s" % testVals[j][0])

        start2 = time.clock()
        x = np.linspace(minq, maxq, 301)
        y = iq_vectorized(coeff, d_max, x)

        end2 = time.clock()
        testVals[j][1] = (end2 - start2)
        print("Time elapsed 2 : %s" % testVals[j][1])

    print("Mean time 1: ", np.mean(testVals[1::, 0]))
    print("Mean time 2: ", np.mean(testVals[1::, 1]))

def demo_npeaks():
    setup = '''
from __main__ import npeaks
import numpy as np
pars = np.arange(1000, dtype = np.float64)
d_max = 2000
nslice = 20'''
    run = '''
print(npeaks(pars, d_max, nslice))'''
    print(timeit.repeat(stmt = run, setup = setup, repeat = 10, number = 1))



def demo_positive_integrals():
    setup = '''
from __main__ import positive_integral_vec
from __main__ import positive_integral
import numpy as np
pars = np.arange(1000)
d_max = 2000
nslice = 21
'''
    run = '''
positive_integral(pars, d_max, nslice)
'''
    run_p = '''
positive_integral(pars, d_max, nslice)
'''
    results_p = np.asanyarray(timeit.repeat(stmt = run_p, setup = setup, repeat = 10, number = 1))

    results_n = np.asanyarray(timeit.repeat(stmt = run, setup = setup, repeat = 10, number = 1))
    test_result_n = positive_integral(np.arange(1000), 2000, 21)
    test_result_p = positive_integral(np.arange(1000), 2000, 21)
    print(test_result_n)
    print(test_result_p)
    print(results_n)
    print(results_p)
    print(results_p / results_n)

@njit()
def test_atleast1d(x):
    if(np.shape(x) == 0):
        return np.sum(np.array(x))
    else:
        return np.sum(x)



def bool_func(x):
    if (x % 2) == 0:
        return True
    return False

@conditional_decorator(njit, bool_func(2))
def condition_test():
    sum = 0.0
    for i in range(1000):
        sum += i ** 2
    return sum

@conditional_decorator(njit, bool_func(1))
def condition_test2():
    sum = 0.0
    for i in range(1000):
        sum += i ** 2
    return sum

def demo_conditional_dec():
    setup = '''
from __main__ import condition_test
from __main__ import condition_test2'''
    run_njit = '''
condition_test()'''
    run_n = '''
condition_test2()'''
    print(timeit.repeat(stmt = run_njit, setup = setup, repeat = 10, number = 1))
    print(timeit.repeat(stmt = run_n, setup = setup, repeat = 10, number = 1))


def demo_iq_smeared_qvec():
    q = np.linspace(0.001, 0.5, 301)
    p = np.arange(40)
    d_max = 2000
    width, height = 0.01, 3
    npts = 30

    setup = '''
from __main__ import iq_smeared_qvec_njit_p
from __main__ import iq_smeared_qvec_njit
from __main__ import iq_smeared_qvec
from __main__ import iq_smeared

import numpy as np
#q = np.linspace(0.001, 0.5, 301)
q = np.arange(301, dtype = np.float64)
p = np.arange(40)
d_max = 2000
width, height = 0.01, 3
npts = 30'''
    codeP = '''iq_smeared_qvec_njit_p(p, q, d_max, height, width, npts)'''
    codeN = '''iq_smeared_qvec_njit(p, q, d_max, height, width, npts)'''
    code = '''iq_smeared_qvec(p, q, d_max, height, width, npts)'''

    #repeat 3 times each executing loop once take minimuim because higher values
    #not usually caused by python by other processes scheduled by os
    print("\n:Vector Testing:\n")

    timesParallel = timeit.repeat(setup = setup, stmt = codeP, repeat = 10, number = 1)
    times = timeit.repeat(setup = setup, stmt = code, repeat = 10, number = 1)
    timesNjit = timeit.repeat(setup = setup, stmt = codeN, repeat = 10, number = 1)


    print("\nParallel Times: \n", timesParallel)
    print("Lowest Time P: ", min(timesParallel))
    print("\nNjit Times: \n", timesNjit)
    print("Lowest Time: ", min(timesNjit))
    print("\nNormal Times: \n", times)
    print("Lowest Time N: ", min(times))


    #To demonstrate same as original C code using arange instead of linspace for easier testing in C,
    #avoid rounding errors perhaps present in linspace().
    #Difference between parallel and normal lower with higher q, with lower q slightly higher error.
    q = np.arange(301, dtype = np.float64)

    test_result_njit = iq_smeared_qvec_njit(p, q, d_max, height, width, npts)
    test_result_p = iq_smeared_qvec_njit_p(p, q, d_max, height, width, npts)
    test_result_n = iq_smeared_qvec(p, q, d_max, height, width, npts)


    print("\nResult Normal (summed): ", np.sum(test_result_n))
    print("Result Parallelized (summed): ", np.sum(test_result_p))
    print("Result Njit (summed) ", np.sum(test_result_njit))

    print("\n**Parallel agaisnt Normal Test-**")
    if(np.array_equal(test_result_p, test_result_n)):
        print("*Identical Results*")
    else:
        print("*Different Results*")
        print("Difference: ")
        print(np.sum(test_result_p))
        print(np.sum(test_result_n))
        print(test_result_p - test_result_n)

    print("\n**Njit agaisnt Normal Test-**")
    if(np.array_equal(test_result_njit, test_result_n)):
        print("*Identical Results*")
    else:
        print("*Different Results*")
        print("Difference: ")
        print(np.sum(test_result_njit))
        print(np.sum(test_result_n))
        print(test_result_njit - test_result_n)

def demo_iq_smeared_scalar():
    q = 0.5
    p = np.arange(40)
    d_max = 2000
    width, height = 0.01, 3
    npts = 30
    setup = '''
from __main__ import iq_smeared_qvec_njit
from __main__ import iq_smeared_qvec
from __main__ import iq_smeared
from __main__ import iq_smeared_p
import numpy as np
#q = np.linspace(0.001, 0.5, 301)
q = 0.5
p = np.arange(40)
d_max = 2000
width, height = 0.01, 3
npts = 30'''
    code = '''iq_smeared(p, d_max, height, width, q, npts)'''
    codeP = '''iq_smeared_p(p, d_max, height, width, q, npts)'''

    #repeat 3 times each executing loop once take minimuim because higher values
    #not usually caused by python by other processes scheduled by os

    print("\n:Scalar Testing:\n")

    times = timeit.repeat(setup = setup, stmt = code, repeat = 10, number = 1)
    timesP = timeit.repeat(setup = setup, stmt = codeP, repeat = 10, number = 1)

    print("\nNormal Times: ", times)
    print("Lowest Time: ", min(times))
    print("\nParallel Times: ", timesP)
    print("Lowest TIme: ", min(timesP))

    test_result = iq_smeared(p, d_max, height, width, q, npts)
    test_result_p = iq_smeared_p(p, d_max, height, width, q, npts)

    print("\nResult: ", test_result)
    if(test_result == test_result_p):
        print("*Same Result*")
    else:
        print("*Different Results*")
        print("Difference: ", test_result - test_result_p)


if(__name__ == "__main__"):
    #demo_iq_smeared_scalar()
    #demo_iq_smeared_qvec()
    #demo_conditional_dec()
    q = np.linspace(0.1, 0.5, 301, dtype = np.float64)
    p = np.arange(40, dtype = np.float64)
    d_max = 2000.0
    width, height = 0.01, 3.0
    npts = np.int(30)
    print(iq_smeared_qvec_njit(p, q, d_max, height, width, npts))

    q = np.atleast_1d(0.5)
    print(iq_smeared_qvec_njit(p, q, d_max, height, width, npts))