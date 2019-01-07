from __future__ import print_function
import numpy as np
import pandas as pd
import inspect
import os
import time

from . import Model
from . import Utils as U

#------------------------------
#FINDING NEAREST NEIGHBOR 
#------------------------------
def mindistance(x,xma,Nx):
    distx = 0
    mindist = 1000000 * U.PC * U.AU 
    j = None

    for i in range(Nx):
        distx = abs(x-xma[i])

        if (distx<mindist):
            mindist=distx
            j=i

    return j

#------------------------------
#OVERLAPING SUBMODELS INTO GRID
#------------------------------
def overlap(GRID, submodels = [''], folder = './Subgrids/', 
            T_min = 30., rho_min = 1.e9,
            all = False, radmc3d = False):
            
    func_name = inspect.stack()[0][3]

    if folder[-1] != '/': folder = folder + '/'
    t0 = time.time()
    num=int(np.loadtxt(os.popen("ls -1 %s*.dat| wc -l"%folder)))
    data=os.popen("ls -1 %s*.dat"%folder).read().split('\n',num)[:-1]
    
    if all:
        names = [name for name in data] # if '_S.' in name or '_MSW' in name] 
        files = [np.loadtxt(name) for name in names]
    
    else:
        submodels = [folder + sub for sub in submodels]
        names = [name for name in submodels] 
        files = [np.loadtxt(name) for name in names]
    
    detected = [tmp.split(folder)[1] for tmp in data]
    read = [tmp.split(folder)[1] for tmp in names]

    print ("Running function '%s'..."%func_name)
    print ('Files detected (%d):'%num, detected, 
           '\nFiles to merge in grid (%d):'%len(files), read)

    NTotal = GRID.NPoints
    Nx, Ny, Nz = GRID.Nodes

    cm3_to_m3 = 1e6
    gamma = 7./5 #Gamma for diatomic molecules
    kb = 1.38064852e-23 #Boltzmann constant
    H_mass = 1.6733e-27 #kg

    DENS = -1*np.ones(NTotal) #, dtype='float64') * 0.5 # * dens_back
    TEMP = np.zeros(NTotal) # * temp_back * dens_back

    ab0 = 5e-8 
    ABUND = np.zeros(NTotal) #np.ones(NTotal) * ab0

    gtd0 = 100.
    GTD = np.zeros(NTotal) #np.ones(NTotal) * gtd0

    VEL = [np.zeros(NTotal),np.zeros(NTotal),np.ones(NTotal)*1*70000] 

#----------------------
#----------------------

#-------------------
#SUBGRIDS DEFINITION
#-------------------

    NFiles = len(files); CountFiles = np.arange(NFiles)
    lenFiles = [len(file) for file in files]

    dens_tmp = [[{},{}] for i in CountFiles] 
    temp_tmp = [{} for i in CountFiles] 
    vel_tmp = [[{} for i in CountFiles] for i in range(3)]
    abund_tmp = [{} for i in CountFiles] 
    gtd_tmp = [{} for i in CountFiles] 

    hg=0
    IDList = [[] for i in CountFiles]

    Xgrid, Ygrid, Zgrid = GRID.XYZgrid 

    for m in range(len(files)):
        for n in files[m]:
        
            x,y,z = n[1], n[2], n[3]

            i = mindistance(x,Xgrid,Nx)
            j = mindistance(y,Ygrid,Ny)
            k = mindistance(z,Zgrid,Nz)
   
            Num = i*(Ny)*(Nz)+j*(Nz)+k; #ID for the Global Grid

            #if Num in IDList[m]: #Really slow as the size of IDList increases
            try:
                dens_tmp[m][0][Num] += n[4]
                dens_tmp[m][1][Num] += 1
                temp_tmp[m][Num] += n[4] * n[5]  
                vel_tmp[0][m][Num] += n[4] * n[6] 
                vel_tmp[1][m][Num] += n[4] * n[7]
                vel_tmp[2][m][Num] += n[4] * n[8]
                abund_tmp[m][Num] += n[4] * n[9]
                gtd_tmp[m][Num] += n[4] * n[10]
            except KeyError:
            #else:
                dens_tmp[m][0][Num] = n[4]
                dens_tmp[m][1][Num] = 1
                temp_tmp[m][Num] = n[4] * n[5]  
                vel_tmp[0][m][Num] = n[4] * n[6] 
                vel_tmp[1][m][Num] = n[4] * n[7]
                vel_tmp[2][m][Num] = n[4] * n[8]
                abund_tmp[m][Num] = n[4] * n[9]
                gtd_tmp[m][Num] = n[4] * n[10]
                IDList[m].append(Num)
        
            #hg+=1
            #if hg%50000 == 0: print (hg)

        print ('Finished merging for: %s'%names[m])

    print ('Computing combined densities, temperatures, etc....')
    for m in range(NFiles):
        for ind in IDList[m]:
        
            dens_tot = dens_tmp[m][0][ind]

            temp_tmp[m][ind] = temp_tmp[m][ind] / dens_tot
            abund_tmp[m][ind] = abund_tmp[m][ind] / dens_tot
            gtd_tmp[m][ind]= gtd_tmp[m][ind] / dens_tot
            vel_tmp[0][m][ind] = vel_tmp[0][m][ind] / dens_tot 
            vel_tmp[1][m][ind] = vel_tmp[1][m][ind] / dens_tot 
            vel_tmp[2][m][ind] = vel_tmp[2][m][ind] / dens_tot 
            dens_tmp[m][0][ind] = dens_tot / dens_tmp[m][1][ind]

            #-------------------
            #FOR THE GLOBAL GRID
            #-------------------

            dens_dum = dens_tmp[m][0][ind]
            temp_dum = temp_tmp[m][ind]
            vel0_dum = vel_tmp[0][m][ind]
            vel1_dum = vel_tmp[1][m][ind]
            vel2_dum = vel_tmp[2][m][ind]
            abund_dum = abund_tmp[m][ind]
            gtd_dum = gtd_tmp[m][ind]

            DENS[ind] += dens_dum
            TEMP[ind] += dens_dum * temp_dum  
            VEL[0][ind] += dens_dum * vel0_dum
            VEL[1][ind] += dens_dum * vel1_dum
            VEL[2][ind] += dens_dum * vel2_dum
            ABUND[ind] += dens_dum * abund_dum
            GTD[ind] += dens_dum * gtd_dum

    TEMP = TEMP / DENS    
    ABUND = ABUND / DENS
    GTD = GTD / DENS
    
    VEL[0] = VEL[0] / DENS
    VEL[1] = VEL[1] / DENS
    VEL[2] = VEL[2] / DENS

    VEL = Model.Struct( **{'x': VEL[0], 'y': VEL[1], 'z': VEL[2]})

    ind = np.where(DENS == -1.0)
    DENS[ind] = rho_min
    ABUND[ind] = ab0 #?
    GTD[ind] = gtd0 #?
    DENS = np.where(DENS < rho_min, rho_min, DENS)
    
    TEMP = np.where(TEMP == 0., T_min, TEMP)

    if radmc3d: pass #Model.Datatab_RADMC3D_FreeFree(DENS,TEMP,GRID)
    else: Model.DataTab_LIME(DENS,TEMP,VEL,ABUND,GTD,GRID)

    AllProp = Model.Struct( **{'GRID': GRID, 'density': DENS, 'temperature': TEMP, 'vel': VEL, 'abundance': ABUND, 'gtd': GTD}) 
    print ('%s is done!'%func_name)
    print ('Ellapsed time: %.3fs' % (time.time() - t0))
    print ('-------------------------------------------------\n-------------------------------------------------')
    
    return AllProp
