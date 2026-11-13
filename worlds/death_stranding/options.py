from dataclasses import dataclass
from Options import Choice, Range, DeathLinkMixin, PerGameCommonOptions, StartInventoryPool


class Goal(Choice):
    """Condition de victoire."""
    display_name = "Objectif"
    option_finish_episode_14 = 0
    option_finish_episode_12 = 1
    default = 0


class TrapPercentage(Range):
    """Pourcentage du remplissage transformé en pièges."""
    display_name = "Pourcentage de pièges"
    range_start = 0
    range_end = 100
    default = 15


class StartingEpisodes(Range):
    """Nombre d'épisodes débloqués au départ en plus de l'épisode 1 (choisis aléatoirement)."""
    display_name = "Épisodes de départ supplémentaires"
    range_start = 0
    range_end = 5
    default = 0


@dataclass
class DeathStrandingOptions(DeathLinkMixin, PerGameCommonOptions):
    goal: Goal
    trap_percentage: TrapPercentage
    starting_episodes: StartingEpisodes
    start_inventory_from_pool: StartInventoryPool
