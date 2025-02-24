"""
Modified from the Pyimagesearch 5-part series on Siamese networks: https://pyimg.co/dq1w5
"""

# External imports
import tensorflow as tf
import matplotlib.pyplot as plt

# Local imports
from siamese_tf.dataset import PairsGenerator, create_dataset, prepare_dataset
from siamese_tf.dataset import CommonMapFunction, AugmentMapFunction
from siamese_tf.model import get_embedding_module
from siamese_tf.model import get_siamese_network
from siamese_tf.model import SiameseModel
import config as config


def visualize_triplets(dataset, n_batches=1):
    """ """

    for i, (anchors, positives, negatives) in enumerate(dataset):

        if i == n_batches:
            break

        fig = plt.figure(figsize=(24, 8))  # w,h
        ax1, ax2, ax3 = fig.subplots(nrows=3, ncols=config.BATCH_SIZE)

        for i in range(0, config.BATCH_SIZE):
            anchor_im = anchors[i].numpy()
            positive_im = positives[i].numpy()
            negative_im = negatives[i].numpy()

            ax1[i].imshow(anchor_im)
            ax2[i].imshow(positive_im)
            ax3[i].imshow(negative_im)

            plt.axis("off")

        plt.tight_layout()
        plt.show()


def save_model(model, name):
    """ """
    print(f"Saving the siamese network to {name}...")
    config.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    tf.keras.models.save_model(
        model=model,
        filepath=config.OUTPUT_PATH / name,
        include_optimizer=True,
    )


####################################################################################################
# Prepare datasets
####################################################################################################

train_generator = PairsGenerator(config.TRAIN_DATASET)
valid_generator = PairsGenerator(config.VALID_DATASET)

train_dataset = create_dataset(train_generator)
valid_dataset = create_dataset(valid_generator)

common_map_fun = CommonMapFunction(image_size=config.IMAGE_SIZE)
aug_map_fun = AugmentMapFunction()

train_ds = prepare_dataset(
    train_dataset, common_map_fun, aug_map_fun, shuffle=True, augment=True
)
valid_ds = prepare_dataset(valid_dataset, common_map_fun, aug_map_fun, augment=True)

visualize_triplets(train_ds, n_batches=1)
visualize_triplets(valid_ds, n_batches=1)


####################################################################################################
# Model loading or creation
####################################################################################################

if config.LOAD_MODEL_PATH is not None and config.LOAD_MODEL_PATH.exists():
    print(f"Loading model {config.LOAD_MODEL_PATH}...")
    siamese_model = tf.keras.models.load_model(filepath=config.LOAD_MODEL_PATH)
    print("Model loaded!")

    # Making densenet trainable causes XLA to take around 16 min to compile it in my machine.
    # Make sure to disable it with `trainable=False` if you don't want to train the backbone anymore.
    siamese_model.siamese_net.get_layer("embedding").get_layer(
        "densenet121"
    ).trainable = config.TRAIN_BACKBONE


else:  # Create new model
    embedding_module = get_embedding_module(
        image_size=config.IMAGE_SIZE, trainable=config.TRAIN_BACKBONE
    )
    print(f"Creating new feature extractor")
    siamese_net = get_siamese_network(
        image_size=config.IMAGE_SIZE, embedding_model=embedding_module
    )
    siamese_model = SiameseModel(siamese_net)

print(f"Is backbone trainable: {config.TRAIN_BACKBONE}")

print(f"Setting learning rate to {config.LEARNING_RATE:.3E}")
optimizer = tf.keras.optimizers.SGD(config.LEARNING_RATE)
siamese_model.compile(optimizer=optimizer)

####################################################################################################
# Define train callbacks
####################################################################################################

ckpt_cb = tf.keras.callbacks.ModelCheckpoint(
    filepath=str(config.MODEL_CKPT_PATH),
    save_freq="epoch",
    monitor="val_loss",
    save_best_only=True,
    initial_value_threshold=config.INITIAL_LOSS,
    verbose=1,
)

tensorboard_cb = tf.keras.callbacks.TensorBoard(log_dir=config.LOGS_PATH)

reduce_lr_cb = tf.keras.callbacks.ReduceLROnPlateau(
    monitor="val_loss", factor=0.5, patience=7, verbose=1, epsilon=1e-4
)

callbacks = [ckpt_cb, tensorboard_cb, reduce_lr_cb]

####################################################################################################
# Train
####################################################################################################

try:
    print("Training the siamese model...")
    siamese_model.fit(
        train_ds,
        steps_per_epoch=config.STEPS_PER_EPOCH,
        validation_data=valid_ds,
        validation_steps=config.VALIDATION_STEPS,
        epochs=config.EPOCHS,
        callbacks=callbacks,
        initial_epoch=config.INITIAL_EPOCH,
    )

except KeyboardInterrupt as e:
    print(f"Interrupted by user!")
