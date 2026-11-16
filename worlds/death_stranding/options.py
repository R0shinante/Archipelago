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


class LikesChecks(Range):
    """Nombre de paliers de likes qui sont des checks (0 = désactivé). Les likes obtenus via des objets Archipelago ne comptent pas."""
    display_name = "Paliers de likes (nombre de checks)"
    range_start = 0
    range_end = 50
    default = 0


class LikesStep(Range):
    """Nombre de likes à gagner pour chaque palier (palier n = n × cette valeur)."""
    display_name = "Likes par palier"
    range_start = 100
    range_end = 10000
    default = 1000


class OrderChecks(Range):
    """Nombre de paliers de progression des commandes qui sont des checks (0 = désactivé). Le compteur monte à chaque étape de commande accomplie
    (livraison standard, commande de bot, objectif d'une commande principale). Les livraisons hors commande ne comptent pas."""
    display_name = "Paliers de progression des commandes (nombre de checks)"
    range_start = 0
    range_end = 100
    default = 0


class OrderStep(Range):
    """Nombre d'étapes de commande à accomplir pour chaque palier (palier n = n × cette valeur)."""
    display_name = "Étapes de commande par palier"
    range_start = 1
    range_end = 50
    default = 3


@dataclass
class DeathStrandingOptions(DeathLinkMixin, PerGameCommonOptions):
    goal: Goal
    trap_percentage: TrapPercentage
    starting_episodes: StartingEpisodes
    likes_checks: LikesChecks
    likes_step: LikesStep
    order_checks: OrderChecks
    order_step: OrderStep
    start_inventory_from_pool: StartInventoryPool
