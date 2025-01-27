#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
September 2020 by Oliver Gurney-Champion & Misha Kaandorp
oliver.gurney.champion@gmail.com / o.j.gurney-champion@amsterdamumc.nl
https://www.github.com/ochampion

Code is uploaded as part of our publication in MRM (Kaandorp et al. Improved unsupervised physics-informed deep learning for intravoxel-incoherent motion modeling and evaluation in pancreatic cancer patients. MRM 2021)

requirements:
numpy
torch
tqdm
matplotlib
scipy
joblib
"""
import numpy as np
import IVIMNET.simulations as sim
from hyperparams import hyperparams as hp_example_1
import IVIMNET.deep as deep
import time
import torch
import IVIMNET.fitting_algorithms as fit

# Import parameters
arg = hp_example_1()
arg.fit.bounds = ([0, 0, 0.05, 0], [0.005, 0.7, 5.0, 2.0])
arg.fit.model = 'ballistic'
arg.sim.bvalues = np.array([0, 5, 10, 20, 30, 100, 200,    5,   10,   20,   30,  100, 200])
arg.sim.cvalues = np.array([0, 0,  0,  0,  0,   0,   0, 0.37, 0.53, 0.74, 0.91, 1.66, 2.35])
arg.sim.model = 'ballistic'
arg.sim.range = ([0.0005, 0.05, 0.5], [0.003, 0.55, 3.5])
arg.sim.SNR = [100]
arg.sim.sims = int(1e6)
arg.net_pars.cons_min = [0, 0, 0.05, 0]  # Dt, Fp, vd, S0
arg.net_pars.cons_max = [0.005, 0.7, 5.0, 2.0]  # Dt, Fp, vd, S0
arg.net_pars.ballistic = True

arg = deep.checkarg(arg)
print(arg.save_name)
for SNR in arg.sim.SNR:
    # this simulates the signal
    IVIM_signal_noisy, D, f, Dp = sim.sim_signal(SNR, arg.sim.bvalues, sims=arg.sim.sims, Dmin=arg.sim.range[0][0],
                                             Dmax=arg.sim.range[1][0], fmin=arg.sim.range[0][1],
                                             fmax=arg.sim.range[1][1], Dsmin=arg.sim.range[0][2],
                                             Dsmax=arg.sim.range[1][2], rician=arg.sim.rician, ballistic=True, cvalues=arg.sim.cvalues)
    
    start_time = time.time()
    # train network
    net = deep.learn_IVIM(IVIM_signal_noisy, arg.sim.bvalues, arg, cvalues=arg.sim.cvalues)
    elapsed_time = time.time() - start_time
    print('\ntime elapsed for training: {}\n'.format(elapsed_time))

    # simulate IVIM signal for prediction
    [dwi_image_long, Dt_truth, Fp_truth, Dp_truth] = sim.sim_signal_predict(arg, SNR)

    # predict
    start_time = time.time()
    paramsNN = deep.predict_IVIM(dwi_image_long, arg.sim.bvalues, net, arg)
    elapsed_time = time.time() - start_time
    print('\ntime elapsed for inference: {}\n'.format(elapsed_time))
    # remove network to save memory
    del net
    if arg.train_pars.use_cuda:
        torch.cuda.empty_cache()

    start_time = time.time()
    # all fitting is done in the fit.fit_dats for the other fitting algorithms (lsq, segmented and Baysesian)
    paramsf = fit.fit_dats(arg.sim.bvalues, dwi_image_long, arg.fit)
    elapsed_time = time.time() - start_time
    print('\ntime elapsed for lsqfit: {}\n'.format(elapsed_time))
    print('results for lsqfit')

    # plot values predict and truth
    sim.plot_example1(paramsNN, paramsf, Dt_truth, Fp_truth, Dp_truth, arg, SNR)
