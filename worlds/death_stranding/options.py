from dataclasses import dataclass
from Options import Choice, Range, Toggle, DeathLinkMixin, PerGameCommonOptions, StartInventoryPool


class Goal(Choice):
    """Victory condition: finish the last main order of episode 14 (default) or of episode 12."""
    display_name = "Goal"
    option_finish_episode_14 = 0
    option_finish_episode_12 = 1
    default = 0


class EpisodeGating(Toggle):
    """Holds back main-order checks until the items "Episode 1 Access" to "Episode N Access" have all been received (N = the order's episode).
    The game itself is not locked: the order finishes normally and its check is sent as soon as the item arrives.
    Likes, order-progress, standard-order and bot-order checks are never held back."""
    display_name = "Hold checks behind episode access"
    default = 0


class TrapPercentage(Range):
    """Percentage of filler items turned into traps."""
    display_name = "Trap percentage"
    range_start = 0
    range_end = 100
    default = 15


class StartingEpisodes(Range):
    """Number of "Episode N Access" items given at the start (episodes drawn at random among those of the game, episode 1 included).
    These items only affect generation logic: the game is not locked."""
    display_name = "Extra starting episodes"
    range_start = 0
    range_end = 5
    default = 0


class LikesChecks(Range):
    """Number of likes milestones that are checks (0 = disabled). Likes received through Archipelago items do not count."""
    display_name = "Likes milestones (check count)"
    range_start = 0
    range_end = 50
    default = 0


class LikesStep(Range):
    """Likes to earn for each milestone (milestone n = n × this value)."""
    display_name = "Likes per milestone"
    range_start = 100
    range_end = 10000
    default = 1000


class OrderChecks(Range):
    """Number of order-progress milestones that are checks (0 = disabled). The counter goes up with every completed order step
    (standard delivery, bot order, objective of a main order). Deliveries made outside an order do not count."""
    display_name = "Order progress milestones (check count)"
    range_start = 0
    range_end = 100
    default = 0


class OrderStep(Range):
    """Order steps to complete for each milestone (milestone n = n × this value)."""
    display_name = "Order steps per milestone"
    range_start = 1
    range_end = 50
    default = 3


class StandardChecks(Range):
    """Number of delivered standard-order milestones that are checks (0 = disabled). The game's own exact counter, read live, no save needed.
    Main orders, bot orders and lost cargo do not count."""
    display_name = "Standard order milestones (check count)"
    range_start = 0
    range_end = 100
    default = 0


class StandardStep(Range):
    """Standard orders to deliver for each milestone (milestone n = n × this value)."""
    display_name = "Standard orders per milestone"
    range_start = 1
    range_end = 50
    default = 3


class BotChecks(Range):
    """Number of delivered bot-order milestones that are checks (0 = disabled). Counter derived from the game's counters, read live, no save needed.
    Known limitation: a recovered lost cargo is counted as a bot delivery."""
    display_name = "Bot order milestones (check count)"
    range_start = 0
    range_end = 100
    default = 0


class BotStep(Range):
    """Bot orders to deliver for each milestone (milestone n = n × this value)."""
    display_name = "Bot orders per milestone"
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
