from keras.applications import VGG16, InceptionV3, ResNet50
from keras.layers import Dense, GlobalAveragePooling2D
from keras.models import Model
from keras.callbacks import EarlyStopping
import numpy as np
from sklearn.utils import compute_class_weight
from sklearn.metrics import precision_recall_curve, recall_score, \
    precision_score, accuracy_score, f1_score, confusion_matrix, roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
import os


class ImageClassifier:
    """
    This class defines a basic image classification model using pre-trained models.
    """

    def __init__(self, input_shape, num_classes=2, activation="sigmoid", base_model_name="VGG16"):
        """
        Initializer for the ImageClassifier class.

        Args:
            input_shape: The input shape for the model (e.g., (120, 120, 3)).
            num_classes: The number of output classes (default: 2).
            activation: The activation function for the final layer (default: sigmoid).
        """
        self.input_shape = input_shape
        self.num_classes = num_classes
        self.activation = activation
        self.base_model_name = base_model_name.lower()  # Ensure case-insensitive selection
        self.model = self._build_model()

    def _build_model(self):
        """
        Builds the image classification model using a pre-trained base model.

        Returns:
            A compiled Keras model.
        """
        # Load the pre-trained base model based on the argument
        if self.base_model_name == "vgg16":
            base_model = VGG16(weights="imagenet", include_top=False, input_shape=self.input_shape + (3,))
        elif self.base_model_name == "inceptionv3":
            base_model = InceptionV3(weights="imagenet", include_top=False, input_shape=self.input_shape + (3,))
        elif self.base_model_name == "resnet50":
            base_model = ResNet50(weights="imagenet", include_top=False, input_shape=self.input_shape + (3,))
        else:
            raise ValueError(f"Unsupported base model name: {self.base_model_name}")

        # Freeze the base model layers (optional for fine-tuning)
        for layer in base_model.layers:
            layer.trainable = False

        # Add custom layers for classification
        x = base_model.output
        x = GlobalAveragePooling2D()(x)
        x = Dense(self.num_classes, activation=self.activation)(x)

        # Create the final model
        model = Model(inputs=base_model.input, outputs=x)

        # Compile the model with optimizer, loss function, and metrics (replace with your choice)
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])

        return model

    def train(self, train_data, validation_data, epochs, step_size_train, step_size_val, class_weights=True,
              augment=True):
        """
        Trains the model on the provided data.

        Args:
            train_data: A Keras ImageDataGenerator object for training data.
            validation_data: A Keras ImageDataGenerator object for validation data.
            epochs: The number of training epochs.
            class_weights: If TRUE, will calculate class weights.
            augment: Was data augmentation performed in the image handler(default: True).
            step_size_train:.
            step_size_val:.

        """
        early_stop = EarlyStopping(monitor="val_loss", patience=13, restore_best_weights=True)

        base_dir = f"models"
        if class_weights:
            # Calculate class weights
            class_weight = compute_class_weight(
                class_weight="balanced",
                classes=np.unique(train_data.classes),
                y=train_data.classes
            )

            weights = {0: class_weight[0], 1: class_weight[1]}
            history = self.model.fit(
                train_data,
                steps_per_epoch=step_size_train,
                epochs=epochs,
                validation_data=validation_data,
                validation_steps=step_size_val,
                class_weight=weights,
                callbacks=[early_stop],
            )
            model_dir = os.path.join(base_dir, f"{self.base_model_name}_with_weights")
            filepath = os.path.join(model_dir, f"{self.base_model_name}_with_weights.h5")

        else:
            history = self.model.fit(
                train_data,
                steps_per_epoch=step_size_train,
                epochs=epochs,
                validation_data=validation_data,
                validation_steps=step_size_val,
                callbacks=[early_stop],
            )
            if augment:
                model_dir = os.path.join(base_dir, f"{self.base_model_name}_data_augmentation")
                filepath = os.path.join(model_dir, f"{self.base_model_name}_data_augmentation.h5")
            else:
                model_dir = os.path.join(base_dir, f"{self.base_model_name}")
                filepath = os.path.join(model_dir, f"{self.base_model_name}.h5")

        os.makedirs(model_dir, exist_ok=True)  # Create directories if they don't exist
        self.model.save(filepath)

        return history

    def evaluate(self, val_data, step_size):
        """
        Evaluates the model on the provided data.

        Args:
            val_data: A Keras ImageDataGenerator object for validation data.
            step_size: A Keras ImageDataGenerator object for validation data.

        Returns:
            The evaluation metrics from the model.
        """
        return self.model.evaluate(val_data,
                                   steps=step_size)

    def test(self, test_generator, step_size_test):
        # Predicting the test data
        prediction = self.model.predict(test_generator,
                                        steps=step_size_test,
                                        verbose=1)
        return prediction

    def plot_training_performance(self, history, class_weights=True, augment=True):
        acc = history.history["accuracy"]
        val_acc = history.history["val_accuracy"]
        loss = history.history["loss"]
        val_loss = history.history["val_loss"]
        num_epochs = len(history.history['loss'])

        # Plotting how the validation and training accuracy was changing with the epochs when the model was training
        plt.figure(figsize=(15, 15))
        plt.subplot(2, 2, 1)
        plt.plot(range(num_epochs), acc, label="Training Accuracy")
        plt.plot(range(num_epochs), val_acc, label="Validation Accuracy")
        plt.legend(loc="lower right")
        plt.title("Training and Validation Accuracy")

        # Plotting how the validation and training loss was changing with the epochs when the model was training
        plt.subplot(2, 2, 2)
        plt.plot(range(num_epochs), loss, label="Training Loss")
        plt.plot(range(num_epochs), val_loss, label="Validation Loss")
        plt.legend(loc="upper right")
        plt.title("Training and Validation Loss")

        # Add the F1 score as text annotation to the plots
        plt.subplot(2, 2, 4)
        plt.text(0.5, 0.5, f'Training Acc: {acc[0]}'
                           f'\n\n Val Acc: {val_acc[0]}\n\n Training Loss: {loss[0]}'
                           f'\n\n Val Loss: {val_loss[0]}\n\n',
                 horizontalalignment='center', verticalalignment='center',
                 transform=plt.gca().transAxes, fontsize=12)

        base_dir = f"graphs"
        if class_weights:
            model_dir = os.path.join(base_dir, f"{self.base_model_name}_with_weights")
        elif augment:
            model_dir = os.path.join(base_dir, f"{self.base_model_name}_data_augmentation")
        else:
            model_dir = os.path.join(base_dir, f"{self.base_model_name}")

        os.makedirs(model_dir, exist_ok=True)  # Create directories if they don't exist
        filepath = os.path.join(model_dir, "training_validation_graphs.png")

        plt.savefig(filepath)
        plt.show()

    def evaluation_metrics(self, prediction, test_generator, class_weights=True, augment=True):
        # Creating an array with all the predictions
        pred = np.argmax(prediction, axis=1)
        true_labels = test_generator.classes

        accuracy = accuracy_score(true_labels, pred)
        f1 = f1_score(true_labels, pred, average='macro')
        roc_auc = roc_auc_score(true_labels, pred)

        prec, recall, _ = precision_recall_curve(true_labels, pred)
        # Plotting the graph of Precision vs Recall
        plt.figure(figsize=(15, 15))
        plt.subplot(2, 2, 1)
        plt.plot(prec, recall)
        plt.title("Precision vs Recall")

        # Add the F1 score as text annotation to the plots
        plt.subplot(2, 2, 2)
        plt.text(0.5, 0.5, f'F1 Score: {f1}\n\n ROC AUC: {roc_auc} Acc: {accuracy}\n\n',
                 horizontalalignment='center', verticalalignment='center',
                 transform=plt.gca().transAxes, fontsize=12)

        base_dir = f"graphs"
        if class_weights:
            model_dir = os.path.join(base_dir, f"{self.base_model_name}_with_weights")
        elif augment:
            model_dir = os.path.join(base_dir, f"{self.base_model_name}_data_augmentation")
        else:
            model_dir = os.path.join(base_dir, f"{self.base_model_name}")

        os.makedirs(model_dir, exist_ok=True)  # Create directories if they don't exist

        filepath = os.path.join(model_dir, "precision_recall_graph.png")
        plt.savefig(filepath)

        # Calculate and plot the confusion matrix for the best model
        conf_mat = confusion_matrix(true_labels, pred)
        class_labels = test_generator.class_indices
        class_names = list(class_labels.keys())

        plt.figure(figsize=(8, 8))
        sns.heatmap(conf_mat, annot=True, fmt='d', cmap='Blues', cbar=False,
                    xticklabels=class_names, yticklabels=class_names)
        plt.title('Confusion Matrix')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')

        filepath = os.path.join(model_dir, "confusion_matrix.png")
        plt.savefig(filepath)

        plt.show()

        print("\nAccuracy:", accuracy)
        print("Precision:", precision_score(true_labels, pred))
        print("Recall:", recall_score(true_labels, pred))
        print("F1 Score:", f1)
        print("ROC AUC Score: ", roc_auc)