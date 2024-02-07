import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision.transforms import ToTensor, RandomHorizontalFlip, RandomVerticalFlip
import numpy as np
from torchvision import transforms
import tifffile
from patchify import patchify, unpatchify
import kornia
import skimage
import cv2
import random
import os
from augmentation import MyAugmentationPipeline
from skimage.transform import downscale_local_mean
import glob

rng = torch.manual_seed(0)
# Defining dataset
class microCT_Dataset(Dataset):

        
    def __init__(self, list_files, HR_patch_size, transform, need_patches,
                 patch_directory=('input_patches/','target_patches/')):
        
        self.patch_sizeHR = HR_patch_size
        self.patch_sizeLR = int(self.patch_sizeHR*2)# patch_size
        
        self.stepHR = HR_patch_size
        self.stepLR = HR_patch_size
        
        if need_patches == True:
            data_path,target_path = self.generate_patches(list_files)
        else:
            
            data_path= patch_directory[0]
            target_path =patch_directory[1]
            
        self.data = glob.glob('input_patches/*')
        self.target = glob.glob('target_patches/*')
        
        self.transform = transform

        
    def generate_patches(self,list_files):
    
        for f in list_files:
            print ('file name: ', f[0])
            t1 = time.time()
            file_tag = f[0][:2]
            data_path = 'data/' + f[0]
            target_path = 'data/' + f[1]
            # reading data and dropping top and bottom layers
            # these layers are empty becasue of registration 
            data = tifffile.imread(data_path)[10:-10,:,:]
            target = tifffile.imread(target_path)[10:-10,:,:]
            
            print ('reading data shape = ', data.shape)
            print ('reading data max = ', data.max())
            
            # contrast stretching to avoid high intensity artifacts
            data = self.contrast_stretching(data)
            
            #padding inputdata to a proper shape by adding half of the 
            # difference between HR and LR patch size to each side of input
            pd = int((self.patch_sizeLR-self.patch_sizeHR)/2)
            #print ('padding amount = ',pd)
            data = np.pad(data, ((pd,pd), (pd,pd), (pd,pd)), mode='constant') 

            # Data and target into patches
    
            data = self.patchyfy_img(data,self.patch_sizeLR,self.stepLR)
            target = self.patchyfy_img(target,self.patch_sizeHR,self.stepHR)
            
            
            print ('out_of_loader data shape = ', data.shape)
            print ('out_of_loader data max = ', data.max())
    
            print ('out_of_loader target shape = ', target.shape)
            print ('out_of_loader target max = ', target.max())
            
            patch_directory=('input_patches/','target_patches/')
            if not os.path.exists(patch_directory[0]):
                os.makedirs(patch_directory[0])
                os.makedirs(patch_directory[1])
            
            if not data.shape[0] == target.shape[0]:
                print ('the patching is not correct!! STOP')
                return None
            
            for i in range(data.shape[0]):
                
                # the input data was upscaled for image registration.
                # now we downscale it back to original
                down_scaled = downscale_local_mean(data[i], (2,2,2))
                
                tifffile.imwrite(patch_directory[0]+file_tag+str(1000+i)+'.tif',down_scaled)
                tifffile.imwrite(patch_directory[1]+file_tag+str(1000+i)+'.tif',target[i])
                
        
            t2=time.time()
            print ('Time = ',round((t2-t1)/60),' minutes')
        return patch_directory
        
    def patchyfy_img(self,img, ps, step):
        img = patchify(img,(ps, ps, ps) ,  step=step )
        print (img.shape)
        img = img.reshape(img.shape[0]*img.shape[1]*img.shape[2],ps,ps,ps )
        return img

    
    def __len__(self):
        return len(self.data)
    
    def contrast_stretching(self,input_image):
        # Contrast stretching
        # Dropping extreems (artifacts)
        p2, p98 = np.percentile(input_image, (2, 98))
        stretched_image = skimage.exposure.rescale_intensity(input_image, in_range=(p2, p98))
        return stretched_image
    
    def __getitem__(self, index):

        data = torch.from_numpy(tifffile.imread(self.data[index])).unsqueeze(0).float()
        target = torch.from_numpy(tifffile.imread(self.target[index])).unsqueeze(0).float()
        
        
        

        
        
        if self.transform is not None:
            
            
            aug = MyAugmentationPipeline()
            data , target = aug.forward(data, target)
            
            #print ('data ot of transformation max = ', data.max())
            # Expanding dimension for batching


        #target = torch.cat(((target<0.5),(target>0.5)), dim=0).float()
        #print ('final target shape', target.shape)
        
        return data, target


'''class ConcatDataset(torch.utils.data.Dataset):
    def __init__(self, *datasets):
        self.datasets = datasets

    def __getitem__(self, i):
        return tuple(d[i] for d in self.datasets)

    def __len__(self):
        return min(len(d) for d in self.datasets)
def train_dataloader(self):
        concat_dataset = ConcatDataset(
            datasets.ImageFolder(traindir_A),
            datasets.ImageFolder(traindir_B)
        )

        loader = torch.utils.data.DataLoader(
            concat_dataset,
            batch_size=args.batch_size,
            shuffle=True,
            num_workers=args.workers,
            pin_memory=True
        )
        '''