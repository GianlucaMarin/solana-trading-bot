# -*- coding: utf-8 -*-
"""
DQN (Deep Q-Network) Agent fuer Trading.

DQN ist ein value-based RL Algorithmus:
- Lernt Q-Values (erwarteter Gewinn pro Action)
- Verwendet Experience Replay Buffer
- Target Network fuer stabile Updates
"""

from typing import Optional, Dict, Any
import os
from pathlib import Path

import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class DQNAgent:
    """
    DQN Agent Wrapper fuer Trading Environment.

    Bietet einfache API fuer:
    - Training
    - Evaluation
    - Model speichern/laden
    """

    def __init__(
        self,
        env,
        learning_rate: float = 1e-4,
        buffer_size: int = 100_000,
        learning_starts: int = 10_000,
        batch_size: int = 128,
        tau: float = 1.0,
        gamma: float = 0.99,
        train_freq: int = 4,
        gradient_steps: int = 1,
        target_update_interval: int = 10_000,
        exploration_fraction: float = 0.1,
        exploration_initial_eps: float = 1.0,
        exploration_final_eps: float = 0.05,
        tensorboard_log: Optional[str] = None,
        verbose: int = 1,
    ):
        """
        Initialisiere DQN Agent.

        Args:
            env: Trading Environment (Gymnasium-kompatibel)
            learning_rate: Learning Rate fuer Optimizer
            buffer_size: Groesse des Replay Buffers
            learning_starts: Steps vor erstem Training
            batch_size: Batch Size fuer Training
            tau: Soft update coefficient (1.0 = hard update)
            gamma: Discount Factor
            train_freq: Training Frequenz (alle N steps)
            gradient_steps: Gradient Steps pro Training
            target_update_interval: Target Network Update Frequenz
            exploration_fraction: Fraction of total steps for exploration
            exploration_initial_eps: Initial epsilon (exploration rate)
            exploration_final_eps: Final epsilon
            tensorboard_log: Pfad fuer TensorBoard Logs
            verbose: Verbosity Level
        """
        self.env = env

        # Wrap Environment fuer Stable-Baselines3
        self.vec_env = DummyVecEnv([lambda: env])

        # Erstelle DQN Model
        self.model = DQN(
            policy="MlpPolicy",
            env=self.vec_env,
            learning_rate=learning_rate,
            buffer_size=buffer_size,
            learning_starts=learning_starts,
            batch_size=batch_size,
            tau=tau,
            gamma=gamma,
            train_freq=train_freq,
            gradient_steps=gradient_steps,
            target_update_interval=target_update_interval,
            exploration_fraction=exploration_fraction,
            exploration_initial_eps=exploration_initial_eps,
            exploration_final_eps=exploration_final_eps,
            verbose=verbose,
            tensorboard_log=tensorboard_log,
        )

        logger.info(
            f"DQN Agent initialisiert mit:\n"
            f"  Learning Rate: {learning_rate}\n"
            f"  Buffer Size: {buffer_size:,}\n"
            f"  Batch Size: {batch_size}\n"
            f"  Gamma: {gamma}\n"
            f"  Exploration: {exploration_initial_eps} -> {exploration_final_eps}"
        )

    def train(
        self,
        total_timesteps: int,
        eval_env=None,
        eval_freq: int = 10000,
        n_eval_episodes: int = 5,
        save_path: Optional[str] = None,
        checkpoint_freq: int = 50000,
    ) -> None:
        """
        Trainiere Agent.

        Args:
            total_timesteps: Anzahl Training Steps
            eval_env: Environment fuer Evaluation
            eval_freq: Evaluation Frequenz (Steps)
            n_eval_episodes: Anzahl Episodes pro Evaluation
            save_path: Pfad zum Speichern des Models
            checkpoint_freq: Checkpoint Frequenz (Steps)
        """
        callbacks = []

        # Evaluation Callback
        if eval_env is not None:
            eval_vec_env = DummyVecEnv([lambda: eval_env])

            eval_callback = EvalCallback(
                eval_vec_env,
                best_model_save_path=save_path if save_path else "./models/",
                log_path=save_path if save_path else "./logs/",
                eval_freq=eval_freq,
                n_eval_episodes=n_eval_episodes,
                deterministic=True,
                render=False,
            )
            callbacks.append(eval_callback)

        # Checkpoint Callback
        if save_path is not None:
            checkpoint_callback = CheckpointCallback(
                save_freq=checkpoint_freq,
                save_path=save_path,
                name_prefix="dqn_checkpoint",
            )
            callbacks.append(checkpoint_callback)

        logger.info(f"Starte Training fuer {total_timesteps} Steps...")

        # Training
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks if callbacks else None,
        )

        logger.info("Training abgeschlossen!")

        # Speichere finales Model
        if save_path is not None:
            final_path = os.path.join(save_path, "dqn_final.zip")
            self.save(final_path)
            logger.info(f"Model gespeichert: {final_path}")

    def predict(self, observation, deterministic: bool = True):
        """
        Vorhersage fuer gegebene Observation.

        Args:
            observation: State Observation
            deterministic: Deterministische Action (True) oder Epsilon-Greedy (False)

        Returns:
            action, state
        """
        action, state = self.model.predict(observation, deterministic=deterministic)
        return action, state

    def evaluate(
        self,
        env,
        n_episodes: int = 10,
        deterministic: bool = True,
    ) -> Dict[str, float]:
        """
        Evaluiere Agent auf Environment.

        Args:
            env: Trading Environment
            n_episodes: Anzahl Test Episodes
            deterministic: Deterministische Actions

        Returns:
            Dictionary mit Metriken
        """
        episode_rewards = []
        episode_lengths = []
        episode_returns = []

        for episode in range(n_episodes):
            obs, info = env.reset()
            done = False
            episode_reward = 0
            episode_length = 0

            while not done:
                action, _ = self.predict(obs, deterministic=deterministic)
                obs, reward, terminated, truncated, info = env.step(action)

                episode_reward += reward
                episode_length += 1
                done = terminated or truncated

            # Episode Stats
            final_return = info.get("total_return", 0)

            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            episode_returns.append(final_return)

            logger.info(
                f"Episode {episode + 1}/{n_episodes}: "
                f"Reward={episode_reward:.2f}, "
                f"Return={final_return*100:.2f}%, "
                f"Length={episode_length}"
            )

        # Aggregate Stats
        stats = {
            "mean_reward": np.mean(episode_rewards),
            "std_reward": np.std(episode_rewards),
            "mean_return": np.mean(episode_returns),
            "std_return": np.std(episode_returns),
            "mean_length": np.mean(episode_lengths),
            "min_return": np.min(episode_returns),
            "max_return": np.max(episode_returns),
        }

        logger.info(
            f"\n=== Evaluation Results ({n_episodes} episodes) ===\n"
            f"Mean Reward: {stats['mean_reward']:.2f} +/- {stats['std_reward']:.2f}\n"
            f"Mean Return: {stats['mean_return']*100:.2f}% +/- {stats['std_return']*100:.2f}%\n"
            f"Return Range: [{stats['min_return']*100:.2f}%, {stats['max_return']*100:.2f}%]\n"
            f"Mean Length: {stats['mean_length']:.1f} steps"
        )

        return stats

    def save(self, path: str) -> None:
        """Speichere Model."""
        # Erstelle Directory falls nicht existiert
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        self.model.save(path)
        logger.info(f"Model gespeichert: {path}")

    def load(self, path: str) -> None:
        """Lade Model."""
        self.model = DQN.load(path, env=self.vec_env)
        logger.info(f"Model geladen: {path}")

    @staticmethod
    def load_agent(path: str, env) -> "DQNAgent":
        """
        Lade gespeicherten Agent.

        Args:
            path: Pfad zum Model
            env: Trading Environment

        Returns:
            DQNAgent Instanz
        """
        agent = DQNAgent(env)
        agent.load(path)
        return agent
