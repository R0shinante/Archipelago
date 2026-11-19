from dataclasses import dataclass
from Options import Choice, Range, Toggle, DeathLinkMixin, PerGameCommonOptions, StartInventoryPool


class Goal(Choice):
    """Condition de victoire."""
    display_name = "Objectif"
    option_finish_episode_14 = 0
    option_finish_episode_12 = 1
    default = 0


class EpisodeGating(Toggle):
    """Retient l'envoi des checks de commandes principales tant que les objets « Episode 1 Access » à « Episode N Access » ne sont pas tous reçus
    (N = épisode de la commande). Le jeu n'est pas verrouillé : la commande se termine normalement et son check part dès que l'objet arrive.
    Les checks de likes, de progression, de commandes standard et de bot ne sont jamais retenus."""
    display_name = "Retenir les checks selon les accès d'épisode"
    default = 0


class TrapPercentage(Range):
    """Pourcentage du remplissage transformé en pièges."""
    display_name = "Pourcentage de pièges"
    range_start = 0
    range_end = 100
    default = 15


class StartingEpisodes(Range):
    """Nombre d'objets « Episode N Access » donnés au départ (épisodes tirés au hasard parmi ceux de la partie, épisode 1 compris).
    Ces objets n'agissent que sur la logique de génération : le jeu n'est pas verrouillé."""
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


class StandardChecks(Range):
    """Nombre de paliers de commandes standard livrees qui sont des checks (0 = désactivé). Compteur exact du jeu, lu en direct, sans sauvegarde.
    Les commandes principales, les commandes de bot et les marchandises perdues ne comptent pas."""
    display_name = "Paliers de commandes standard (nombre de checks)"
    range_start = 0
    range_end = 100
    default = 0


class StandardStep(Range):
    """Nombre de commandes standard à livrer pour chaque palier (palier n = n × cette valeur)."""
    display_name = "Commandes standard par palier"
    range_start = 1
    range_end = 50
    default = 3


class BotChecks(Range):
    """Nombre de paliers de commandes de bot livrees qui sont des checks (0 = désactivé). Compteur déduit des compteurs du jeu, lu en direct, sans sauvegarde."""
    display_name = "Paliers de commandes de bot (nombre de checks)"
    range_start = 0
    range_end = 100
    default = 0


class BotStep(Range):
    """Nombre de commandes de bot à livrer pour chaque palier (palier n = n × cette valeur)."""
    display_name = "Commandes de bot par palier"
    range_start = 1
    range_end = 50
    default = 3


@dataclass
class DeathStrandingOptions(DeathLinkMixin, PerGameCommonOptions):
    goal: Goal
    episode_gating: EpisodeGating
    trap_percentage: TrapPercentage
    starting_episodes: StartingEpisodes
    likes_checks: LikesChecks
    likes_step: LikesStep
    order_checks: OrderChecks
    order_step: OrderStep
    standard_checks: StandardChecks
    standard_step: StandardStep
    bot_checks: BotChecks
    bot_step: BotStep
    start_inventory_from_pool: StartInventoryPool
