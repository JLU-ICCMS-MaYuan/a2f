import os
import re

import numpy as np
from pymatgen.core.structure import IStructure

from constants import k_bohr_A


class Folder(object):
    """
    Parses a folder with QE ph.x calculations,
    then gives paths to different output files
    and also the prefix (formula)
    """
    __path = ''
    dyn_elph_paths = list()
    ph_outs_paths = list()
    scf_outs_paths = list()
    dyns = list()

    def __init__(self, path):
        self.__path = path
        self.dyn_paths = self.dyns()
        self.dyn_elph_paths = self.dyn_elphs()
        self.ph_outs_paths = self.ph_outs()
        self.scf_outs_paths = self.scf_outs()

    def dyns(self):
        dyn_paths = list(filter(lambda x: 'dyn' in x and 'elph' not in x and 'dyn0' not in x, os.listdir(self.__path)))
        full_dyns_paths = sorted([os.path.join(self.__path, dyn_path) for dyn_path in dyn_paths])
        if full_dyns_paths:
            print(f'Found dyns in {", ".join(full_dyns_paths)}')
            return full_dyns_paths
        else:
            print(f'WARNING: Unable to detect *dyn* files in {self.__path}')

    def dyn_elphs(self):
        dyn_elphs_paths = list(filter(lambda x: 'elph' in x, # lambda x: 'dyn' in x and 'elph' in x,
                                      os.listdir(self.__path)))
        full_dyn_elphs_paths = sorted([os.path.join(self.__path, dyn_elphs_path) for dyn_elphs_path in dyn_elphs_paths])
        if full_dyn_elphs_paths:
            # print(f'Found dyn_elphs in {", ".join(full_dyn_elphs_paths)}')
            print(f'Found elphs in {", ".join(full_dyn_elphs_paths)}')
            return full_dyn_elphs_paths
        else:
            # print(f'ERROR: Unable to detect *dyn*.elph* files in {self.__path}')
            print(f'ERROR: Unable to detect *elph* files in {self.__path}')
            raise FileNotFoundError

    def ph_outs(self):
        # ph_outs_paths = list(filter(lambda x: '.ph' in x and 'out' in x,
        #                             os.listdir(self.__path)))
        ph_outs_paths = list(filter(lambda x: 'ph' in x and 'out' in x,
                                    os.listdir(self.__path)))
        full_ph_outs_paths = [os.path.join(self.__path, ph_outs_path) for ph_outs_path in ph_outs_paths]
        if full_ph_outs_paths:
            print(f'Found ph.outs in {", ".join(full_ph_outs_paths)}')
            return full_ph_outs_paths
        else:
            print('Warning: Unable to detect ph.out files in ', self.__path)
            return list()
        
    def scf_outs(self):
        scf_outs_paths = list(filter(lambda x: 'scf' in x and 'out' in x,
                                    os.listdir(self.__path)))
        full_scf_outs_paths = [os.path.join(self.__path, scf_outs_path) for scf_outs_path in scf_outs_paths]
        if full_scf_outs_paths:
            print(f'Found scf.outs in {", ".join(full_scf_outs_paths)}')
            return full_scf_outs_paths
        else:
            print('Warning: Unable to detect ph.out files in ', self.__path)
            return list()
        
    def a2f_dats(self, *p):
        a2f_dats_paths = list(filter(lambda x: 'a2F.dat' in x, os.listdir(self.__path)))
        if a2f_dats_paths:
            if len(a2f_dats_paths) == 1:
                return a2f_dats_paths[0]
            else:
                print('Warning: Detected several a2F.dat files in ', self.__path)
                print('Specify which to parse')
                return a2f_dats_paths[p]
        else:
            print('Warning: Unable to detech a2F.dat files in ', self.__path)
            return [self.__path]

    def formula(self):
        formula = os.path.basename(self.dyn_elphs()[0]).split(".")[0]
        return formula


class Dyn(object):
    """
    Parses a single *dyn*.elph* file,
    returning all it contains:
    q-point, lambdas, gammas and squared frequencies
    """
    lines = list()
    q_point = tuple()
    weight = float()

    def __init__(self, path):
        with open(path) as read_obj:
            lines = read_obj.readlines()
            read_obj.close()
        self.lines = lines
        self.q_point()
        self.weight()
        print(f'q = ({", ".join(["%.3f" % round(_q, 3) for _q in self.q_point])}) '
              f'with number of q in the star {int(self.weight)}')

    def q_point(self):
        q_idx = int()
        for idx, line in enumerate(self.lines):
            if 'q = (' in line:
                q_idx = idx
                break
        self.q_point = tuple(float(x) for x in self.lines[q_idx].split()[-4:-1])
        return self.q_point

    def weight(self):
        self.weight = 0
        for line in self.lines:
            if 'Diagonalizing the dynamical matrix' in line:
                break
            if 'q = (' in line:
                self.weight = self.weight + 1
        # self.weight = float(self.lines[2].split()[1])
        return self.weight


class DynElph(object):
    """
    Parses a single *dyn*.elph* file,
    returning all it contains:
    q-point, lambdas, gammas and squared frequencies
    """
    lines = list()
    q_point = tuple()
    sqr_freqs = list()
    dos_line = str()
    E_F = float()
    DOS = float()
    lambda_gamma_lines = list()
    lambdas = list()
    gammas = list()

    def __init__(self, path):
        with open(path) as read_obj:
            lines = read_obj.readlines()
            read_obj.close()
        self.lines = lines
        headers = ['Gaussian Broadening', 'Tetrahedron method']
        headers_idx = list()
        for i, line in enumerate(lines):
            for header in headers:
                if header in line:
                    headers_idx.append(i)
        headers_idx.append(len(lines)) # headers_idx保存着'Gaussian Broadening', 'Tetrahedron method'字符串所在的行号
        self.headers_idx = headers_idx
        self.headers = list()
        self.dos_lines = list()
        self.lambda_gamma_lines = list()
        for i in range(len(headers_idx) - 1):
            i1 = headers_idx[i]
            i2 = headers_idx[i + 1]
            self.dos_lines.append(next(line for line in lines[i1:i2] if 'DOS' in line)) #获取每个展宽对应的dos，el_ph_nsigma的个数决定了展宽的个数，el_ph_sigma决定了展宽的宽度。
            self.lambda_gamma_lines.append(list(filter(lambda x: 'lambda' in x and 'gamma' in x, lines[i1:i2])))
            if 'Gaussian Broadening' in lines[i1]:
                header = float(lines[i1].split()[2]) # 如果是包含'Gaussian Broadening'的行，会记录展宽宽度和展宽编号
            else:
                header = lines[i1] # 如果是包含'Tetrahedron Broadening'，则什么都不会记录
            self.headers.append(header)
        self.length = len(self.headers)
        self.q_point()
        self.sqr_freqs()
        self.e_fermi()
        self.dos()
        self.lambdas()
        self.gammas()
        for i, lambdas in enumerate(self.lambdas):
            # print(self.lambdas[i])
            # print(self.gammas[i])
            if np.any(lambdas < 0):
                if self.length > 1:
                    print(
                        f'WARNING: found negative lambdas in {path} (Broadening = {self.headers[i]}). They and their gammas will be zeroed.')
                else:
                    print(f'WARNING: found negative lambdas in {path}. They and their gammas will be zeroed.')
                idx = np.where(lambdas < 0)
                self.lambdas[i][idx] = 0
                self.gammas[i][idx] = 0
                # rint(self.lambdas[i])
                # rint(self.gammas[i])
                # assert False
            # print(np.sum(lambdas))

    def q_point(self):
        self.q_point = tuple(float(x) for x in self.lines[0].split()[0:3])
        return self.q_point

    def sqr_freqs(self):
        '''
        功能：该方法是用来获得elph.imp_lambda文件中第2行到broadening行的所有频率的平方
        '''
        lines = self.lines
        sqr_freqs = list()
        # idx = lines.index(next(line for line in lines if 'method' in line))
        for line in lines[1:self.headers_idx[0]]:
            for freq in line.strip().split():
                sqr_freqs.append(float(freq))
        self.sqr_freqs = np.array(sqr_freqs)
        return self.sqr_freqs

    def e_fermi(self):
        self.E_F = list()
        for dos_line in self.dos_lines:
            self.E_F.append(float(re.search('Ef(.*)eV', dos_line).group(1).replace('=', '')))
        return self.E_F

    def dos(self):
        self.DOS = list()
        for dos_line in self.dos_lines:
            self.DOS.append(float(re.search('DOS(.*)states', dos_line).group(1).replace('=', '')))
        return self.DOS

    def lambdas(self):
        self.lambdas = list()
        for each in self.lambda_gamma_lines:
            lambdas = list()
            for line in each:
                lambdas.append(float(line.split('=')[1].split()[0]))
            self.lambdas.append(np.array(lambdas))
        return self.lambdas

    def gammas(self):
        self.gammas = list()
        for each in self.lambda_gamma_lines:
            gammas = list()
            for line in each:
                gammas.append(float(line.split('=')[2].split()[0]))
            self.gammas.append(np.array(gammas))
        return self.gammas

    def as_dict(self):
        dyn_elph_dict = {
            'q_point': self.q_point,
            'sqr_freqs': self.sqr_freqs,
            'e_fermi': self.e_fermi,
            'dos': self.dos,
            'lambdas': self.lambdas,
            'gammas': self.gammas
        }
        return dyn_elph_dict


class PhOuts(object):
    """
    Parses given list of ph.out files,
    returns weights (and soon will be parsing frequencies).
    Works both with multiple ph.out files
    and single ph.out file.
    """
    __lines = list()
    weights = list()
    __alat = float()
    __matrix = np.zeros((3, 3))
    __n_atoms = int()
    __species = list()
    __coords = list()
    structure = IStructure
    __paths = list()

    def __init__(self, paths):
        self.__paths = paths
        if len(paths) > 1 or (len(paths) == 1 and not os.path.isdir(paths[0])):
            for path in paths:
                with open(path, 'r') as f:
                    _lines = f.readlines()
                self.__lines.append(_lines)

    def weights(self):
        """
        Output format: (q-points, weights)
        :return:
        """
        self.weights = list()
        q_points = list()
        if self.__lines:
            for _lines in self.__lines:
                weight_lines = list(filter(lambda x: 'number of k points=' in x and 'method' in x, _lines)) # 没什么用
                occupancies = [i for i, x in enumerate(_lines) if 'Number of q in the star' in x] # 权重所在行号
                for occupancy in occupancies:
                    q_point = tuple([float(x) for x in _lines[occupancy + 2].strip().split()[-3:]])
                    weight = int(_lines[occupancy].split()[-1]) # 权重是weigh, 就表示有weigh个等价的q点
                    print(f'q = ({", ".join(["%.3f" % round(_q, 3) for _q in q_point])}) '
                          f'with number of q in the star {weight}')
                    q_points.append(q_point)
                    self.weights.append(weight)
        else:
            print('Assuming no-symmetry calculation, consequently setting uniform weights')
            self.weights = [1] * len(Folder(self.__paths[0]).dyn_elphs())
        weights_sum = sum(self.weights)
        weights = [weight / weights_sum for weight in self.weights]
        self.weights = list(zip(q_points, weights))
        return self.weights

    def struc(self):
        """
        Reads first structure that appears in the ph.out files.
        :return: pymatgen IStructure
        """
        idxs = dict()
        keys = ['lattice parameter (alat)', 'a(1)', 'a(2)', 'a(3)', 'site n.', 'number of atoms/cell']
        flag = 0
        for i, lines in enumerate(self.__lines):
            for j, line in enumerate(lines):
                for key in keys:
                    if key in line:
                        if key not in idxs.keys():
                            idxs[key] = (i, j)
                            flag = flag + 1
            if flag == len(keys):
                break

        idx = idxs['lattice parameter (alat)']
        self.__alat = float(self.__lines[idx[0]][idx[1]].split()[4])  # alat in bohr
        for i, key in enumerate(['a(1)', 'a(2)', 'a(3)']):
            idx = idxs[key]
            split = self.__lines[idx[0]][idx[1]].split()
            self.__matrix[i] = np.array([float(split[3]), float(split[4]), float(split[5])])
        self.__matrix = self.__matrix * self.__alat
        idx = idxs['number of atoms/cell']
        self.__n_atoms = int(self.__lines[idx[0]][idx[1]].split()[-1])
        idx = idxs['site n.']
        for i in range(idx[1] + 1, idx[1] + 1 + self.__n_atoms):
            split = self.__lines[idx[0]][i].split()
            a1, a2, a3 = self.__matrix
            coords = [float(split[-4]) * self.__alat,
                      float(split[-3]) * self.__alat,
                      float(split[-2]) * self.__alat]
            self.__coords.append(coords)
            self.__species.append(split[1])
        self.__coords = np.array(self.__coords) * k_bohr_A
        self.__matrix = np.array(self.__matrix) * k_bohr_A
        self.structure = IStructure(lattice=self.__matrix, species=self.__species, coords=self.__coords,
                                    coords_are_cartesian=True)
        return self.structure


class ScfOuts(object):
    def __init__(self, paths):
        self.__paths = paths

    def struc(self):
        """
        Reads first structure that appears in the ph.out files.
        :return: pymatgen IStructure
        """
        from ase.io import read
        from pymatgen.io.ase import AseAtomsAdaptor
        if len(self.__paths ) > 1 or (len(self.__paths ) == 1 and not os.path.isdir(self.__paths [0])):
            ase_type = read(self.__paths[0])
            self.structure = AseAtomsAdaptor.get_structure(ase_type)
            return self.structure
