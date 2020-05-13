import torch.optim as optim
import numpy as np
import torch.nn as nn
import ray
import torch
import os
import pickle
import yaml
import pdb

from ray.tune.schedulers import ASHAScheduler, AsyncHyperBandScheduler
from models.LSTMnet4 import lstm
from ray import tune
from swdata import swDataset
from lfnets import train, test, get_loaders, send_finished_email

#################################################
#-----------------CONFIGURATION-----------------#
experimentDir = '/usr/scratch/charles/data/randSearches/'
experimentNm = 'rand_search'

data = {"file": '/usr/scratch/charles/data/13T15DataNoTS.pickle',
        "norm": True,
        "vType": "seq",
        "epochs": 512,
        "nMods": 128
        }

hparams = {"lr": (-4, -1),
           "wd": (-7, -1),
           "bs": (128, 1024),
           "hs": (32, 256),
        }
#################################################
#------------------DO NOT EDIT------------------# 
config = {"data": data,
          "hpars": hparams}
# Create new project directory
tmpNm = experimentNm
count = 0
while(os.path.isdir(experimentDir + tmpNm)):
        tmpNm = experimentNm + str(count)
        count = count + 1
experimentNm = tmpNm        

# Try to create all necessary directories
os.system('mkdir ' + experimentDir )
os.system('mkdir '  + experimentDir + experimentNm)

# Write experiment config file
with open(experimentDir + experimentNm + '/config.yml', 'w+') as f:
        yaml.dump(config, f)
# Assemble training, validation, and testing datasets
train_dataset = swDataset(dataFile = data["file"], split='train', valType = data["vType"], normalize = data["norm"], portion = 1)
val_dataset = swDataset(dataFile = data["file"], split='val', valType = data["vType"], normalize = data["norm"], portion = 1)
test_dataset = swDataset(dataFile = data["file"], split='test', valType = data["vType"], normalize = data["norm"], portion = 1)

# Get dimensions of data
_, in_seq_len, in_dim = val_dataset.valData.size()
_, out_seq_len, out_dim = val_dataset.valLabels.size()

## Initialize the ray hyperparameter search
ray.init(num_cpus=64, num_gpus=4)

train_dataset = ray.put(train_dataset)
val_dataset = ray.put(val_dataset)
test_dataset = ray.put(test_dataset)
# Build RAY Trainable class
class trainModel(tune.Trainable):
    def _setup(self, config):

        self.train_dataset = ray.get(train_dataset)
        self.val_dataset = ray.get(val_dataset)
        self.test_dataset = ray.get(test_dataset)
        datasets = (self.train_dataset, self.val_dataset, self.test_dataset)
        # Get Data Loaders using lfnets function
        self.train_loader, self.val_loader, self.test_loader = get_loaders(datasets, data["vType"], data["norm"], 1, config["batch_size"], True)

        ## Build Model with hyperparameters
        self.model = lstm(input_dim=in_dim, output_dim=out_dim, hidden_dim=config["hs"], n_layers=3, in_seq_len=in_seq_len, out_seq_len=out_seq_len)
        ## Build Optimizer with optimization hyperparameters
        self.optimizer = optim.Adam(
            self.model.parameters(), lr=config["lr"], weight_decay=config["wd"]
        )
        self.config = config
        use_cuda = torch.cuda.is_available()
        self.device = ("cuda" if use_cuda else "cpu")
        self.model.to(self.device)    

    def _train(self):
        train(self.model, self.optimizer, self.train_loader, metric=nn.MSELoss(), device=self.device)
        acc = test(self.model, self.val_loader, metric=nn.MSELoss(), device=self.device).cpu().item()
        return {'mean_squared_error': acc}
    
    def _save(self, checkpoint_dir):
        checkpoint_path = os.path.join(checkpoint_dir, "model.pt")
        torch.save(self.model, checkpoint_path)
        return checkpoint_path

    def _restore(self, checkpoint_path):
        self.model.load_state_dict(torch.load(checkpoint_path))

# Scheduler for job scheduling
async_hb_scheduler = AsyncHyperBandScheduler(
    time_attr='training_iteration',
    metric='mean_squared_error',
    mode='min',
    max_t=256,
    grace_period=10,
    reduction_factor=3,
    brackets=3)

# Actual run call
analysis = tune.run(
    trainModel,
    name = experimentNm,
    config={
        "lr": tune.sample_from(lambda spec: 10**(np.random.uniform(hparams["lr"][0], hparams["lr"][1]))), 
        "wd": tune.sample_from(lambda spec: 10**(np.random.uniform(hparams["wd"][0], hparams["wd"][1]))),
        "batch_size": tune.sample_from(lambda spec: np.random.randint(hparams["bs"][0], hparams["bs"][1])),
        "hs": tune.sample_from(lambda spec: np.random.randint(hparams["hs"][0], hparams["hs"][1]))
        },
    resources_per_trial={
        "cpu": 1,
        "gpu": 1
        },
    stop={
        "training_iteration": data["epochs"]
        },
    num_samples = data["nMods"],
    local_dir=experimentDir,
    verbose=1,
    checkpoint_at_end=True,
    scheduler=async_hb_scheduler,
    raise_on_failed_trial=False
)

send_finished_email()

# Open tensorboard in the experiment directory for remote running
os.system('tensorboard --logdir ' + experimentDir + experimentNm)
