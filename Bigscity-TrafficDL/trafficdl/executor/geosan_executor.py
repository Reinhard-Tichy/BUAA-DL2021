import json
import torch
import torch.optim as optim
import numpy as np
import os
from tqdm import tqdm
import time as Time
from trafficdl.executor.abstract_executor import AbstractExecutor
import random
from trafficdl.utils import get_evaluator

class GeoSANExecutor(AbstractExecutor):

    def __init__(self, config, model):
        super().__init__(config, model)
        self.config = config
        self.device = self.config.get('device', torch.device('cpu'))
        self.model = model.to(self.device)
        self.evaluator = get_evaluator(config)
        self.evaluate_res_dir = './trafficdl/cache/evaluate_cache'

    def train(self, train_dataloader, eval_dataloader):
        """
        use data to train model with config

        Args:
            train_dataloader(torch.Dataloader): Dataloader
            eval_dataloader(torch.Dataloader): None
        """
        num_epochs = self.config['executor_config']['train']['num_epochs']
        optimizer = optim.Adam(self.model.parameters(), 
                lr=float(self.config['executor_config']['optimizer']['learning_rate']), 
                    betas=(0.9, 0.98))
        self.model.train()
        for epoch_idx in range(num_epochs):
            start_time = Time.time()
            running_loss = 0.
            processed_batch = 0
            batch_iterator = tqdm(enumerate(train_dataloader), 
                total=len(train_dataloader), leave=True)
            for batch_idx, batch in batch_iterator:
                optimizer.zero_grad()
                loss = self.model.calculate_loss(batch)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()
                processed_batch += 1
                batch_iterator.set_postfix_str(f"loss={loss.item():.4f}")
            epoch_time = Time.time() - start_time
            print("epoch {:>2d} completed.".format(epoch_idx + 1))
            print("time taken: {:.2f} sec".format(epoch_time))
            print("avg. loss: {:.4f}".format(running_loss / processed_batch))
            print("epoch={:d}, loss={:.4f}".format(epoch_idx + 1, running_loss / processed_batch))
        print("training completed!")


    def evaluate(self, test_dataloader):
        """
        use model to test data

        Args:
            test_dataloader(torch.Dataloader): Dataloader
        """
        self.evaluator.clear()
        self.model.eval()
        self.reset_random_seed(42)
        with torch.no_grad():
            for _, batch in enumerate(test_dataloader):
                output = self.model.predict(batch)
                # shape: [(1+K)*L, N]
                self.evaluator.collect(output)
        self.evaluator.save_result(self.evaluate_res_dir)

        

    def load_model(self, cache_name):
        """
        加载对应模型的 cache

        Args:
            cache_name(str): 保存的文件名
        """
        self.model.load(cache_name)
        

    def save_model(self, cache_name):
        """
        将当前的模型保存到文件

        Args:
            cache_name(str): 保存的文件名
        """
        self.model.save(cache_name)
        
    def reset_random_seed(seed):
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)