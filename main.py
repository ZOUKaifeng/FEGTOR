
#3.334363660844155, acc 0.9754098360655737, loss 0.6908055394887924

import os


import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import math
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold
import matplotlib.pyplot as plt

from model import DisenFace

import numpy as np
import scipy.sparse as sp
import  open3d as o3d
from scipy.linalg import orthogonal_procrustes

import math


data_list = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise"]
labels_map = {}
for i in range(6):
    labels_map[i] = data_list[i]

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
EPS = 1e-6


C = - 0.5 * math.log( 2 * math.pi)

class FaceData(Dataset):
    def __init__(self, data, label, mask): 
        self.pts = data
        self.labels = label
        self.length = len(data)
        self.mask = mask

        
        
    def __len__(self):

        return self.length

    def __getitem__(self, idx):
        pc = self.pts[idx]
     #   pc = np.reshape(self.pts[idx], (100, 83,3))  # 100x249 => 100x83x3
        # pc, coeff = on_unit_cube(pc)

        mask = np.expand_dims(self.mask[idx], -1)
        pc = pc * mask


        pc = torch.FloatTensor(pc)

        # s = torch.FloatTensor([coeff['scale']])
        # m = torch.FloatTensor(coeff['min'])
        y = self.labels[idx]
        return pc, y, mask





def KLD(mu, log_sigma):
    return -0.5 * torch.sum(1 + log_sigma - mu.pow(2) - (log_sigma).exp(), -1)
def gaussian_nll(mu, log_sigma, x):
    return 0.5 * torch.pow((x - mu) / log_sigma.exp(), 2) + log_sigma + 0.5 * np.log(2 * np.pi)

def loss_funtion(results, pts, mask):
   
    log_sigma = torch.FloatTensor([1]).to(device)


    gaussian_loss = F.mse_loss(results["x"], pts, reduction = 'mean')


  #  gaussian_loss = gaussian_nll( results["x"], log_sigma ,pts).sum(1).sum(1)
    kld_loss = KLD(results["mean"], results["log_sigma"]).mean()
    return  gaussian_loss + lam*kld_loss


def train_step(net, dataloader, optimizer):
    net.train()
    total_loss = []
    total_data = 0
    total_error = 0
    correct = 0
    train_results = {}
    for data in dataloader:
        pts, label, mask = data
        pts, label, mask = pts.to(device).float(), label.to(device), mask.to(device)
        bs = pts.shape[0]
        total_data += bs
        
        

        y_one_hot = torch.zeros(label.shape[0], 6)

        y_one_hot.scatter_(1, label.type(torch.LongTensor).unsqueeze(1), 1)

        y_one_hot = torch.clamp(y_one_hot, EPS, 1-EPS).to(device)

        results = net(pts, y_one_hot, mask)
        
        loss = loss_funtion(results, pts, mask)
        
        
        
        loss.backward()
        optimizer.step()
        
        error = ((torch.abs(pts-results["x"])*mask)*std).mean().item()

        total_error += error
        
        total_loss.append(loss.item())
        
    train_results["error"] = total_error/len(dataloader)
    train_results["loss"] = np.mean(total_loss)
    
    
    return train_results
    
def valid_step(net, dataloader):
    net.eval()
    total_loss = []
    total_data = 0
    total_error = 0
    correct = 0
    valid_results = {}
    with torch.no_grad():
        for data in dataloader:
            pts, label, mask = data
            pts, label, mask = pts.to(device).float(), label.to(device), mask.to(device)
            bs = pts.shape[0]
            total_data += bs

            

            y_one_hot = torch.zeros(label.shape[0], 6)

            y_one_hot.scatter_(1, label.type(torch.LongTensor).unsqueeze(1), 1)

            y_one_hot = torch.clamp(y_one_hot, EPS, 1-EPS).to(device)

            results = net(pts, y_one_hot, mask, False)
            
            loss = loss_funtion(results, pts, mask)
        

            error = ((torch.abs(pts-results["x"])*std)).mean().item()

            total_error += error

            total_loss.append(loss.item())

    valid_results["error"] = total_error/len(dataloader)
    valid_results["loss"] = np.mean(total_loss)
    
    
    return valid_results

# def find_zeros(gt, pred):
#     #bs, 100, 249
#     gt_sum =
def visulization( displacement, filename, first_frame = None):
    #first frame: , 1, 249
    #displacement: , 99, 249
 

    

    data = np.zeros((100, 249))
    if first_frame:
        data[0] = first_frame
        for i, f in enumerate(displacement):
            
            data[i+1] = data[i] + f
    else:
        for i, f in enumerate(displacement):
            data[i] = f
    np.save( filename, data)


def test_step(net, dataloader):
    net.eval()
    total_loss = []
    total_data = 0
    total_error = 0
    correct = 0
    test_results = {}
    recon = []
    with torch.no_grad():
        for i, data in enumerate(dataloader):
            pts, label, mask = data
            pts, label, mask = pts.to(device).float(), label.to(device), mask.to(device)
            bs = pts.shape[0]
            total_data += bs


            y_one_hot = torch.zeros(label.shape[0], 6)

            y_one_hot.scatter_(1, label.type(torch.LongTensor).unsqueeze(1), 1)

            y_one_hot = torch.clamp(y_one_hot, EPS, 1-EPS).to(device)

            results = net(pts, y_one_hot, mask, False)

            loss = loss_funtion(results, pts, mask)

            error = ((torch.abs(pts-results["x"])*mask)*std).mean().item()
            total_error += error


            total_loss.append(loss.item())


            # reconstruction = (results["x"]*mask).cpu().numpy()+m

            # for s in reconstruction:
            #     recon.append(s)



            if i == len(dataloader)-1:
                print("disentangle data")
                for a, p in enumerate(pts):
                #    p = (p).cpu().numpy()
                    p =( p * mask[i]*std ).cpu().numpy() + m_data
                    print(label[a])
                    visulization( p, checkpoint+'/sub_'+str(a)+data_list[label[a]]+'_gt.npy')

                
                z = results['mean']
                for i in range(6):
                    y = torch.ones_like(label).to(device) * i
                    y_one_hot = torch.zeros(y.shape[0], 6)

                    y_one_hot.scatter_(1, y.type(torch.LongTensor).unsqueeze(1), 1)

                    y_one_hot = torch.clamp(y_one_hot, EPS, 1-EPS).to(device)*2
                
                    

                    disenResults = net.sample(z, y_one_hot, mask)
                    disenResults = (disenResults*std).cpu().numpy()+m_data
                    disenResults = disenResults * mask.cpu().numpy()
                    for n, sub in enumerate(disenResults):
                        print(np.sum(sub))
               
                        visulization( sub, checkpoint+data_list[i]+'_'+str(n)+'.npy')



    test_results["error"] = total_error/len(dataloader)
    test_results["loss"] = np.mean(total_loss)
    test_results["reconstruction"] = np.array(recon)
    
    return test_results

def Displacement(subject):
    # subject (606, 100, 249) 

    masks = []


    data = []
    displace = []
    for sub in subject:

        mask = np.ones(100)
        disp = np.zeros((100, 249))
        for i, frame in enumerate(sub):




            if frame.max() - frame.min() != 0:


                
                disp[i] = frame
                data.append(frame)

            else:
                mask[i] = 0
                disp[i] = frame
        displace.append(disp)

        masks.append(mask)
    return np.array(displace), np.array(masks), np.array(data)

lam = 1e-5
num_frame = 100
num_pts = 83
z = 50
c = 6
epochs = 300
lr = 0.000001
weight_decay = 0.0001
label_size = 6
latent_size = 64
hidden_unit = 256
num_head = 4
dropout = 0.1
num_layers = 3
data_path = 'dataset.pkl'
dataset = np.load(data_path, allow_pickle=True)
subject = np.array(dataset["data"])
labels =  np.array(dataset["labels"])
subject = np.reshape(subject, (606, 100 , 249))
displace, masks, data = Displacement(subject)
m_data = data.mean(0)
std = data.std(0)

trainsformed_data = (displace-m_data)/std
std = torch.tensor(std).to(device)


random_seeds = 2021
test_size = 0.2
best_loss = 1000000
net = DisenFace(3*num_pts, num_frame, label_size, hidden_unit, latent_size, num_head,num_layers, dropout).to(device)
checkpoint = './results/transformer/'
if not os.path.exists(checkpoint):
    os.makedirs(checkpoint)
skf = RepeatedStratifiedKFold(n_splits=5, n_repeats=1, random_state = random_seeds) 
for train_index, test_index in skf.split(subject, labels):
    train, valid= train_test_split(train_index, test_size=test_size, random_state = random_seeds)
    
    
    train_data = trainsformed_data[train]
    train_labels = labels[train]
    train_mask = masks[train]

    print("number of train data:", train_data.shape[0])
    #mean, std, train_data = normalize(train_data)
    train_dataset = FaceData(train_data, train_labels, train_mask)
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True, num_workers=4)
    
    valid_data = trainsformed_data[valid]
    valid_labels = labels[valid]
    vallid_mask = masks[valid]
    print("number of valid data:", valid_data.shape[0])
   # _, _, valid_data = normalize(valid_data, mean = mean, std = std)
    valid_dataset = FaceData(valid_data, valid_labels, vallid_mask)
    valid_loader = DataLoader(valid_dataset, batch_size=16, shuffle=True, num_workers=4)
    optimizer = torch.optim.Adam(net.parameters(), lr=lr, weight_decay=weight_decay)
#    std = torch.FloatTensor(std).unsqueeze(0).unsqueeze(0).to(device)

    for ep in range(epochs):
        train_results = train_step(net,  train_loader, optimizer)
        valid_results = valid_step(net,  valid_loader)
    
        print("epoch {}, training: error {},loss {}".format(ep,  train_results["error"], train_results["loss"]))
        print(" validation: error {}, loss {}".format( valid_results["error"], valid_results["loss"]))
        if best_loss>valid_results["loss"]:
            best_loss = valid_results["loss"]
            torch.save(net,checkpoint+ 'DisenFace_LSTM.pt')


    test_data = trainsformed_data[test_index]
    test_labels = labels[test_index]
    test_mask = masks[test_index]
    print("number of test data:", test_data.shape[0])
    test_dataset = FaceData(test_data, test_labels, test_mask)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=True, num_workers=4)
    net = torch.load(checkpoint + '/DisenFace_LSTM.pt')
    test_results = test_step(net,  test_loader)
    print(" test: error {},  loss {}".format( test_results["error"], test_results["loss"]))
    break