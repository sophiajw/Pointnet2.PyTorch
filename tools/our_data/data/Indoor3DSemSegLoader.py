from __future__ import (
    division,
    absolute_import,
    with_statement,
    print_function,
    unicode_literals,
)
import torch
import torch.utils.data as data
import numpy as np
import os
import h5py
import subprocess
import shlex

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#BASE_DIR = "/workspace/pointnet_train"
#BASE_DIR = "/home/lorenzlamm/Dokumente/pointnet_Pytorch_test/pointnetPytorch/pointnet2/data"
BASE_DIR = "/home/lorenzlamm/Dokumente/sshaoshuai/Pointnet2.PyTorch/tools/our_data/data"


def _get_data_files(list_filename):
    with open(list_filename) as f:
        return [line.rstrip() for line in f]

def _load_data_file(name):
    print(name)
    f = h5py.File(name)
    print(f.keys())
    data = f["points"][:]
    label = f["labels"][:]
    print(np.unique(label))
    return data, label


class Indoor3DSemSeg(data.Dataset):
    def __init__(self, num_points, train=True, download=True, data_precent=1.0, overfit = False):
        super().__init__()
        self.data_precent = data_precent
        self.folder = "pn_train_data"
        self.data_dir = os.path.join(BASE_DIR, self.folder)
        self.url = (
            "https://shapenet.cs.stanford.edu/media/indoor3d_sem_seg_hdf5_data.zip"
        )
        download = False
        if download and not os.path.exists(self.data_dir):
            zipfile = os.path.join(BASE_DIR, os.path.basename(self.url))
            subprocess.check_call(
                shlex.split("curl {} -o {}".format(self.url, zipfile))
            )

            subprocess.check_call(
                shlex.split("unzip {} -d {}".format(zipfile, BASE_DIR))
            )

            subprocess.check_call(shlex.split("rm {}".format(zipfile)))

        self.train, self.num_points = train, num_points

        all_files = _get_data_files(os.path.join(self.data_dir, "all_files.txt"))
        #room_filelist = _get_data_files(
        #    os.path.join(self.data_dir, "room_filelist.txt")
        #)

        data_batchlist, label_batchlist = [], []
        for f in all_files:
            data, label = _load_data_file(os.path.join(self.data_dir,f))
            data_batchlist.append(data)
            label_batchlist.append(label)
        data_batches = np.concatenate(data_batchlist, 0)
        labels_batches = np.concatenate(label_batchlist, 0)
        overfit = False
        if(overfit):
            data_batches = data_batches[:2,:,:]
            labels_batches = labels_batches[:2,:]
        labels_unique = np.unique(labels_batches)
        labels_unique_count = np.stack([(labels_batches == labels_u).sum() for labels_u in labels_unique])
        print('count of labels: ')#, labels_unique_count)
        for i in range(labels_unique_count.shape[0]):
            print(i+1, labels_unique_count[i])

        labelSum = labels_unique_count.sum()
        self.weights = np.zeros(21)
        for c in range(21):
            if(c in labels_unique):
                count = 0
                for k in range(21):
                    if(c == k):
                        self.weights[count] = labels_unique_count[count] / labelSum
                    if(k in labels_unique):
                        count += 1
            else:
                self.weights[c] = 1
        #self.weights = labels_unique_count / (labels_unique_count.sum())
        for c in range(21):
            if(c == 0):
                self.weights[c] = 1.0
            else:
                if(c in labels_unique):
                    self.weights[c] = 1 / np.log(1.2 + self.weights[c])
                else:
                    self.weights[c] = 1.0
        print(self.weights, "<----------------------------------------------------------------")
        test_area = "Area_5"
        train_idxs, test_idxs = [], []
        
        for i in range(data_batches.shape[0]):
            if(i % 10 == 0):
                test_idxs.append(i)
            else:
                train_idxs.append(i)
        
        #for i, room_name in enumerate(room_filelist):
        #    if test_area in room_name:
        #        test_idxs.append(i)
        #    else:
        #        train_idxs.append(i)

        if self.train:
            self.points = data_batches[train_idxs, ...]
            self.labels = labels_batches[train_idxs, ...]
        else:
            self.points = data_batches[test_idxs, ...]
            self.labels = labels_batches[test_idxs, ...]

    def __getitem__(self, idx):
        pt_idxs = np.arange(0, self.num_points)
        np.random.shuffle(pt_idxs)

        current_points = torch.from_numpy(self.points[idx, pt_idxs].copy()).type(
            torch.FloatTensor
        )
        current_labels = torch.from_numpy(self.labels[idx, pt_idxs].copy()).type(
            torch.LongTensor
        )
        return current_points, current_labels

    def __len__(self):
        return int(self.points.shape[0] * self.data_precent)

    def set_num_points(self, pts):
        self.num_points = pts

    def get_weights(self):
        weights = torch.from_numpy(self.weights)
        return weights

    def randomize(self):
        pass


if __name__ == "__main__":
    dset = Indoor3DSemSeg(16, "./", train=True)
    print(dset[0])
    print(len(dset))
    dloader = torch.utils.data.DataLoader(dset, batch_size=32, shuffle=True)
    for i, data in enumerate(dloader, 0):
        inputs, labels = data
        if i == len(dloader) - 1:
            print(inputs.size())
