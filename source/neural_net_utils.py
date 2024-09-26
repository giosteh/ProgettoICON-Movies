import torch
from torch import nn
from torch.utils.data import TensorDataset, DataLoader, random_split

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report

from supervised_utils import prepare_data

sns.set_style("whitegrid")


# setting del device
device = "cuda" if torch.cuda.is_available() else "cpu"



# funzione che definisce l'architettura della rete
def define_net_architecture(input_dim):
    # definisco l'architettura della rete
    layers = [input_dim, 64, 64, 32, 16, 8]

    # costruisco la rete
    layers_list = []
    for i in range(len(layers) - 1):
        layers_list.append(nn.Linear(layers[i], layers[i + 1]))
        layers_list.append(nn.ReLU())
        if i > 0:
            layers_list.append(nn.Dropout(p=.2))

    return layers_list


# neural net per il task di regressione
class RegressionNet(nn.Module):

    def __init__(self, input_dim):
        super(RegressionNet, self).__init__()

        layers_list = define_net_architecture(input_dim)
        layers_list.append(nn.Linear(8, 1))

        self.net = nn.Sequential(*layers_list)

        # inizializzazione dei pesi
        self._initialize_weights()

    # metodo per l'inizializzazione dei pesi
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 1)
                nn.init.constant_(m.bias, 0)
    
    # metodo di forward propagation
    def forward(self, x):
        y = self.net(x)
        return y


# neural net per il task di classificazione
class ClassificationNet(nn.Module):

    def __init__(self, input_dim, num_classes):
        super(ClassificationNet, self).__init__()

        layers_list = define_net_architecture(input_dim)
        layers_list.append(nn.Linear(8, num_classes))

        self.net = nn.Sequential(*layers_list)

        # inizializzazione dei pesi
        self._initialize_weights()
    
    # metodo per l'inizializzazione dei pesi
    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 1)
                nn.init.constant_(m.bias, 0)
    
    # metodo di forward propagation
    def forward(self, x):
        y = self.net(x)
        return y


# classe che implementa l'early-stopping
class EarlyStopping:

    def __init__(self, patience=15, dir_path="nets", model_name="model.pt", mode="max"):
        self._patience = patience
        self._counter = 0
        self._best_score = None
        self._stop = False
        self.mode = mode
        self._checkpoint_path = f"{dir_path}/{model_name}"

        self._train_scores = []
        self._val_scores = []
    
    # metodo che controlla se il modello migliora
    def _is_improvement(self, score):
        if self._mode == "max":
            return score > self._best_score
        else:
            return score < self._best_score
    
    # metodo che verifica se il modello migliora
    def __call__(self, train_score, val_score):
        self._train_scores.append(train_score)
        self._val_scores.append(val_score)
        score = val_score

        if self._best_score is None:
            self._best_score = score
        elif self._is_improvement(score):
            self._save_checkpoint()
            self._best_score = score
            self._counter = 0
        else:
            self._counter += 1
            if self._counter >= self._patience:
                self._stop = True
        
        return self._stop

    # metodo che salva il modello
    def _save_checkpoint(self):
        torch.save(self._model.state_dict(), self._checkpoint_path)
    
    # metodo che plotta i risultati
    def plot_scores(self):
        score_name = "Accuracy" if self._mode == "max" else "Loss"
        title = f"Model performance (best {score_name}: {self._best_score:.4f})"

        plt.figure(figsize=(8, 5))
        plt.plot(self._train_scores, label=f"Train {score_name}", linestyle="dashed", linewidth=2.3)
        plt.plot(self._val_scores, label=f"Val {score_name}", linewidth=2.7)
        plt.xlabel("Epoch")
        plt.ylabel(score_name)
        plt.title(title)
        plt.legend()

        plt.show()


# classe che implementa il trainer
class Trainer:

    def __init__(self, df, cols, task="regression", num_classes=None):
        self._task = task
        self._train_loader, self._val_loader, self._test_loader, self._input_dim = self._get_data_loaders(df, cols, task=task)
        self._model = RegressionNet(self._input_dim) if task == "regression" else ClassificationNet(self._input_dim, num_classes)
        self._model.to(device)

        self._criterion = nn.MSELoss() if task == "regression" else nn.CrossEntropyLoss()
        self._optimizer = torch.optim.Adam(self._model.parameters(), lr=1e-2)

        self._model_name = f"{task}-net.pt"
        self._early_stopping = EarlyStopping(model=self._model, model_name=self._model_name)
        self._early_stopping.mode = "min" if task == "regression" else "max"

    # metodo che prepara i data loaders
    def _get_data_loaders(self, df, cols, features_subset=None, batch_size=64,
                          val_split=0.2, resample=False, task="regression"):
        X_train, X_test, y_train, y_test = prepare_data(df, cols, resample=resample, task=task)

        if features_subset:
            X_train = X_train[features_subset]
            X_test = X_test[features_subset]

        train_dataset = TensorDataset(torch.tensor(X_train.values, dtype=torch.float32),
                                      torch.tensor(y_train.values, dtype=torch.float32).reshape(-1, 1))
        test_dataset = TensorDataset(torch.tensor(X_test.values, dtype=torch.float32),
                                     torch.tensor(y_test.values, dtype=torch.float32).reshape(-1, 1))

        train_size = int(len(train_dataset) * (1 - val_split))
        val_size = len(train_dataset) - train_size
        train_dataset, val_dataset = random_split(train_dataset, [train_size, val_size])

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
        test_loader = DataLoader(test_dataset, batch_size=batch_size)

        return train_loader, val_loader, test_loader, X_train.shape[1]
    
    # metodo che esegue il training per un'epoca
    def _train(self):
        self._model.train()

        correct = 0
        size = len(self._train_loader.dataset)

        total_loss = .0
        for features, labels in self._train_loader:
            features = features.to(device)
            labels = labels.to(device)

            logits = self._model(features)
            loss = self._criterion(logits, labels)

            # backpropagation
            self._optimizer.zero_grad()
            loss.backward()
            self._optimizer.step()

            total_loss += loss.item()

            if self._task == "classification":
                predicted = logits.argmax(dim=-1)
                correct += (predicted == labels).sum().item()

        total_loss /= size
        if self._task == "classification":
            accuracy = 100 * correct / size
            return total_loss, accuracy
        else:
            return total_loss, None

    # metodo che esegue la validazione
    def _validate(self):
        self._model.eval()

        correct = 0
        size = len(self._val_loader.dataset)

        total_loss = .0
        with torch.no_grad():
            for features, labels in self._val_loader:
                features = features.to(device)
                labels = labels.to(device)

                logits = self._model(features)
                loss = self._criterion(logits, labels)

                total_loss += loss.item()

                if self._task == "classification":
                    predicted = logits.argmax(dim=-1)
                    correct += (predicted == labels).sum().item()

        total_loss /= size
        if self._task == "classification":
            accuracy = 100 * correct / size
            return total_loss, accuracy
        else:
            return total_loss, None

    # metodo che esegue il test
    def test(self):
        self._model.eval()

        correct = 0
        size = len(self._test_loader.dataset)

        total_loss = .0
        with torch.no_grad():
            for features, labels in self._test_loader:
                features = features.to(device)
                labels = labels.to(device)

                logits = self._model(features)
                loss = self._criterion(logits, labels)

                total_loss += loss.item()

                if self._task == "classification":
                    predicted = logits.argmax(dim=-1)
                    correct += (predicted == labels).sum().item()

        total_loss /= size
        if self._task == "classification":
            accuracy = 100 * correct / size
            return total_loss, accuracy
        else:
            return total_loss, None

    # metodo che esegue il training della rete
    def fit(self, epochs=100, verbose=True):
        for epoch in range(epochs):
            train_loss, train_acc = self._train()
            val_loss, val_acc = self._validate()

            train_score, val_score = train_acc, val_acc if self._task == "classification" else train_loss, val_loss
            stop = self._early_stopping(train_score, val_score)

            if verbose:
                print(f"\nEpoch #{epoch+1}/{epochs} [")
                if self._task == "classification":
                    print(f"Train loss: {train_loss:.4f}, Train accuracy: {train_acc:.4f}")
                    print(f"Val loss: {val_loss:.4f}, Val accuracy: {val_acc:.4f}\n]")
                else:
                    print(f"Train loss: {train_loss:.4f}\nVal loss: {val_loss:.4f}\n]")

            if stop:
                if verbose:
                    print(f"Early stopping at epoch #{epoch+1}")
                break
